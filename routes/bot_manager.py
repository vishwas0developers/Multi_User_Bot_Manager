from flask import Blueprint, request, redirect, url_for, session, jsonify, flash # Ensure jsonify is imported
# Import secure_filename
from werkzeug.utils import secure_filename
from utils.upload_utils import get_user_paths, is_upload_allowed, create_venv_if_missing, install_requirements # Removed save_uploaded_files import if logic moved here
# Import necessary functions from db_utils
from utils.db_utils import (
    get_db, get_user_id, get_user_plan, save_bot_to_db,
    update_button_metadata, get_user_apps, save_uploaded_app,
    delete_app_from_db, get_app_by_name, get_plan_limit # Add get_plan_limit
)
import os
import shutil
import zipfile
import subprocess
from datetime import datetime
import platform
import time # Import the time module for sleep
import tempfile # Add tempfile import

bot_bp = Blueprint('bot_bp', __name__)

# Define the base static image folder path relative to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
STATIC_IMAGE_FOLDER = os.path.join(PROJECT_ROOT, "static", "user_images")
os.makedirs(STATIC_IMAGE_FOLDER, exist_ok=True)

@bot_bp.route("/upload", methods=["POST"])
def upload_app():
    if "google_id" not in session:
        # For API-like endpoints, returning JSON error might be better than redirect
        return jsonify({"error": "unauthorized", "message": "User not logged in."}), 401

    zip_file = request.files.get("zip_file")
    image = request.files.get("image")
    button_name = request.form.get("button_name", "").strip()

    if not zip_file or not button_name:
        # Return JSON error for missing fields
        return jsonify({"error": "missing_data", "message": "ZIP file and button name are required."}), 400

    google_id = session["google_id"]
    user_id = session.get("user_id")

    if not user_id:
         # Return JSON error for session issue
        return jsonify({"error": "session_error", "message": "User session error. Please log in again."}), 400

    # --- Check User Plan Limit ---
    current_plan = get_user_plan(google_id)
    plan_limit = get_plan_limit(current_plan)
    user_apps = get_user_apps(user_id)
    current_app_count = len(user_apps)

    if current_app_count >= plan_limit:
        # Return JSON response instead of flash/redirect
        limit_message = f"You have reached your app limit ({plan_limit} apps) for the '{current_plan}' plan. Please upgrade your plan to upload more apps."
        return jsonify({"error": "limit_reached", "message": limit_message}), 403 # 403 Forbidden is appropriate
    # --- End Plan Limit Check ---

    # --- Check if app name already exists for this user ---
    existing_app = get_app_by_name(user_id, button_name)
    if existing_app:
        # Return JSON response for existing app name
        return jsonify({"error": "name_exists", "message": f"An app with the name '{button_name}' already exists. Please use a unique name."}), 409 # 409 Conflict is appropriate
    # --- End Check ---


    # Get paths: temp_upload_path (for initial zip save), final_app_dir_base
    temp_upload_path, final_app_dir_base, _ = get_user_paths(google_id)

    # Valid folder name
    folder_name = secure_filename(button_name.replace(' ', '_').lower())
    if not folder_name:
        # Return JSON error for invalid name
        return jsonify({"error": "invalid_name", "message": "Invalid button name resulting in empty folder name."}), 400

    # Final destination paths
    final_app_dir = os.path.join(final_app_dir_base, folder_name)
    final_user_image_dir = os.path.join(STATIC_IMAGE_FOLDER, str(google_id), folder_name)
    image_filename = "icon.png"
    final_image_save_path = os.path.join(final_user_image_dir, image_filename)
    image_url_path = f"user_images/{google_id}/{folder_name}/{image_filename}" # Relative path for url_for

    # --- Create a temporary directory for staging the new app ---
    temp_stage_dir = None # Initialize
    try:
        # Create a unique temporary directory within the user's app base or a system temp area
        # Using user's base might be better for permissions, but ensure it's cleaned up
        temp_stage_dir = tempfile.mkdtemp(prefix=f"{folder_name}_stage_", dir=final_app_dir_base)
        print(f"ℹ️ Staging new app in: {temp_stage_dir}")

        # --- Save and Extract ZIP to Temporary Stage Directory ---
        # Use a more unique temp zip name to avoid potential collisions if uploads are very fast
        temp_zip_filename = f"{folder_name}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.zip"
        temp_zip_path = os.path.join(temp_upload_path, temp_zip_filename)
        zip_file.save(temp_zip_path)

        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_stage_dir)
        os.remove(temp_zip_path)
        print(f"✅ ZIP extracted to temporary stage: {temp_stage_dir}")

        # --- Handle Nested Folder in Temporary Stage Directory ---
        extracted_items = os.listdir(temp_stage_dir)
        if len(extracted_items) == 1:
            potential_nested_folder = os.path.join(temp_stage_dir, extracted_items[0])
            if os.path.isdir(potential_nested_folder):
                print(f"ℹ️ Detected nested folder in stage: {potential_nested_folder}. Moving contents up.")
                temp_nested_content_dir = tempfile.mkdtemp(dir=os.path.dirname(temp_stage_dir)) # Temp dir to hold items during move
                for item_name in os.listdir(potential_nested_folder):
                    shutil.move(os.path.join(potential_nested_folder, item_name), os.path.join(temp_nested_content_dir, item_name))
                shutil.rmtree(potential_nested_folder) # Remove original nested
                # Move contents back into the main stage dir
                for item_name in os.listdir(temp_nested_content_dir):
                     shutil.move(os.path.join(temp_nested_content_dir, item_name), os.path.join(temp_stage_dir, item_name))
                shutil.rmtree(temp_nested_content_dir) # Clean up intermediate temp dir
                print(f"✅ Contents moved and nested stage folder removed.")

        # --- Venv and Requirements in Temporary Stage Directory ---
        temp_venv_path = os.path.join(temp_stage_dir, "venv")
        create_venv_if_missing(temp_venv_path)
        req_path = os.path.join(temp_stage_dir, "requirements.txt")
        if os.path.exists(req_path):
            install_requirements(temp_venv_path, req_path, cwd=temp_stage_dir)
        print(f"✅ Virtual environment created and requirements installed in stage.")

        # --- Prepare Image ---
        temp_image_save_path = None
        final_image_url = "/static/images/default-icon.png" # Default
        if image:
             # Save image temporarily first, move it later after cleanup
             temp_image_save_path = os.path.join(temp_upload_path, f"{folder_name}_{image_filename}")
             image.save(temp_image_save_path)
             # We'll set the final_image_url after successful deployment
             print(f"✅ Image temporarily saved to {temp_image_save_path}")


        # --- STAGING COMPLETE - NOW HANDLE EXISTING APP ---

        # --- Backup and Remove existing app (if exists) ---
        if os.path.exists(final_app_dir):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_base = os.path.join(PROJECT_ROOT, "backup", str(google_id))
            backup_dir = os.path.join(backup_base, f"{folder_name}_{timestamp}")
            try:
                os.makedirs(os.path.dirname(backup_dir), exist_ok=True)
                # Copy before attempting removal
                shutil.copytree(final_app_dir, backup_dir, dirs_exist_ok=True) # Use dirs_exist_ok for robustness
                print(f"✅ Backup created at {backup_dir}")

                # Robust rmtree logic for final app and image dirs
                retries = 5 # Increased retries
                delay = 1
                for i in range(retries):
                    try:
                        if os.path.exists(final_app_dir):
                            shutil.rmtree(final_app_dir)
                            print(f"✅ Successfully removed existing app directory: {final_app_dir}")
                        if os.path.exists(final_user_image_dir):
                            shutil.rmtree(final_user_image_dir)
                            print(f"✅ Successfully removed existing image directory: {final_user_image_dir}")
                        break # Success
                    except PermissionError as e:
                        print(f"⚠️ Attempt {i+1}/{retries}: PermissionError removing {final_app_dir} or {final_user_image_dir}: {e}. Retrying after {delay}s...")
                        time.sleep(delay)
                    except OSError as e:
                         # Specifically check for "Directory not empty" which might happen if deletion is slow
                        if e.winerror == 145 and platform.system() == "Windows":
                             print(f"⚠️ Attempt {i+1}/{retries}: Directory not empty error removing {final_app_dir} or {final_user_image_dir}. Retrying after {delay}s...")
                        else:
                             print(f"⚠️ Attempt {i+1}/{retries}: OSError removing {final_app_dir} or {final_user_image_dir}: {e}. Retrying after {delay}s...")
                        time.sleep(delay)
                    except Exception as e: # Catch broader exceptions during removal
                        flash(f"Unexpected error removing existing app/image directory: {e}", "error")
                        raise # Re-raise to be caught by the main try-except block
                else: # If loop completes without break
                    flash(f"❌ Failed to remove existing app/image directory after {retries} attempts. Upload aborted.", "error")
                    # Clean up backup? Optional.
                    # shutil.rmtree(backup_dir)
                    raise Exception("Failed to remove existing directories.") # Raise to trigger cleanup

            except Exception as backup_remove_err:
                 flash(f"Error during backup/removal process for {folder_name}: {backup_remove_err}", "error")
                 raise # Re-raise to be caught by the main try-except block

        # --- Move Staged App to Final Location ---
        shutil.move(temp_stage_dir, final_app_dir)
        temp_stage_dir = None # Mark as moved
        print(f"✅ Staged app moved to final location: {final_app_dir}")

        # --- Save Image to Final Location ---
        os.makedirs(final_user_image_dir, exist_ok=True) # Ensure final image dir exists
        if temp_image_save_path and os.path.exists(temp_image_save_path):
            shutil.move(temp_image_save_path, final_image_save_path)
            final_image_url = url_for('static', filename=image_url_path, _external=False)
            print(f"✅ Image moved to final location: {final_image_save_path}")
            print(f"✅ Final Image URL set to: {final_image_url}")
        elif image: # If image was provided but temp save failed or wasn't needed
             image.seek(0) # Reset stream position if needed
             image.save(final_image_save_path)
             final_image_url = url_for('static', filename=image_url_path, _external=False)
             print(f"✅ Image saved directly to final location: {final_image_save_path}")
             print(f"✅ Final Image URL set to: {final_image_url}")
        else:
             print(f"ℹ️ No image provided or saved, using default.")


        # --- Save App Info to DB ---
        # Check if an app with the same folder_name exists (could happen if sanitization leads to collision, though less likely now)
        # This part might need adjustment if we strictly rely on button_name uniqueness check earlier.
        # However, keeping the DB save logic as is should be fine.
        save_uploaded_app(
            google_id=google_id,
            user_id=user_id,
            button_name=button_name,
            folder_name=folder_name,
            image_url=final_image_url # Use the determined final URL
        )
        print(f"✅ App metadata saved to DB for {folder_name}")

        # --- Re-register apps ---
        try:
            from app import register_all_apps
            register_all_apps()
        except Exception as e:
            print(f"⚠️ Error re-registering apps: {e}")
            # Even if re-register fails, the upload was successful file-wise
            # Maybe return a specific success code/message? Or just redirect.
            flash("App uploaded, but failed to dynamically load it. A server restart might be needed.", "warning")
            # Still redirect on success, flash message will show on dashboard
            return redirect(url_for("user_bp.dashboard"))


        # If everything succeeded, flash success and redirect
        flash(f"App '{button_name}' uploaded successfully!", "success")
        return redirect(url_for("user_bp.dashboard")) # Redirect on success

    except zipfile.BadZipFile:
        flash("Invalid ZIP file.", "error")
    except subprocess.CalledProcessError as e:
        flash(f"Failed to install dependencies: {e.stderr}", "error")
    except Exception as e:
        flash(f"An error occurred during upload: {e}", "error")
        print(f"❌ Upload failed: {e}") # Log the specific error
        # Return a generic server error JSON response
        return jsonify({"error": "upload_failed", "message": f"An error occurred during upload: {e}"}), 500
    finally:
        # Cleanup logic remains the same
        if temp_stage_dir and os.path.exists(temp_stage_dir):
            try:
                shutil.rmtree(temp_stage_dir)
                print(f"✅ Cleaned up temporary stage directory: {temp_stage_dir}")
            except Exception as cleanup_err:
                print(f"⚠️ Error cleaning up temporary stage directory {temp_stage_dir}: {cleanup_err}")
        # Clean up temp zip if it still exists (e.g., early exit)
        if 'temp_zip_path' in locals() and os.path.exists(temp_zip_path):
             try:
                 os.remove(temp_zip_path)
                 print(f"✅ Cleaned up temporary zip file: {temp_zip_path}")
             except Exception as cleanup_err:
                 print(f"⚠️ Error cleaning up temporary zip file {temp_zip_path}: {cleanup_err}")
        # Clean up temp image if it still exists
        if 'temp_image_save_path' in locals() and temp_image_save_path and os.path.exists(temp_image_save_path):
             try:
                 os.remove(temp_image_save_path)
                 print(f"✅ Cleaned up temporary image file: {temp_image_save_path}")
             except Exception as cleanup_err:
                 print(f"⚠️ Error cleaning up temporary image file {temp_image_save_path}: {cleanup_err}")

        # Removed the faulty redirect check from here:
        # if flash is not None and any(cat == 'error' for _, cat in flash(None, '_flashes')):
        #      return redirect(url_for("user_bp.dashboard"))

    # If an exception occurred before the success redirect, the function ends here,
    # and the user sees the flashed error message on the dashboard (after the implicit redirect).
    # If no exception occurred, the success redirect in the try block was already executed.
    # We might need an explicit redirect here ONLY if an error happens AFTER the main try block
    # but before the function naturally ends. However, the current structure handles this.
    # Adding a default redirect here might mask issues. Let's rely on the success redirect
    # and flashed messages for errors.
    # If execution reaches here after an error, it means the error was caught and flashed.
    # A redirect back to the dashboard is appropriate in that case.
    # Check if an error was flashed *before* this point might be complex.
    # Let's assume the default behavior (ending the function) is sufficient for now.
    # If errors aren't redirecting properly, we might need to adjust the except blocks.
    return redirect(url_for("user_bp.dashboard")) # Add a default redirect at the end in case of error fallthrough


@bot_bp.route("/edit/<folder_name>", methods=["POST"])
def edit_script(folder_name):
    new_button_name = request.form.get("button_name", "").strip()
    new_zip_file = request.files.get("zip_file")
    new_image_file = request.files.get("image")

    google_id = session.get("google_id")
    base_path, script_dir, venv_path = get_user_paths(google_id)
    app_path = os.path.join(script_dir, folder_name)

    if not os.path.exists(app_path):
        return jsonify({"status": "error", "message": "App folder not found."}), 404

    if new_zip_file and new_zip_file.filename:
        shutil.rmtree(app_path)
        os.makedirs(app_path, exist_ok=True)

        zip_path = os.path.join(script_dir, f"{folder_name}_temp_edit.zip")
        new_zip_file.save(zip_path)

        temp_extract_target = os.path.join(script_dir, f"temp_extract_edit_{folder_name}")
        if os.path.exists(temp_extract_target):
            shutil.rmtree(temp_extract_target)
        os.makedirs(temp_extract_target, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_extract_target)
        except Exception as e:
            os.remove(zip_path)
            shutil.rmtree(temp_extract_target)
            return jsonify({"status": "error", "message": f"Extraction failed: {e}"}), 500
        finally:
            os.remove(zip_path)

        extracted_items = os.listdir(temp_extract_target)
        source_dir_for_move = os.path.join(temp_extract_target, extracted_items[0]) if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_target, extracted_items[0])) else temp_extract_target
        for item in os.listdir(source_dir_for_move):
            shutil.move(os.path.join(source_dir_for_move, item), app_path)
        shutil.rmtree(temp_extract_target)

        py_files = [f for f in os.listdir(app_path) if f.endswith(".py") and f != '__init__.py']
        main_py_path = os.path.join(app_path, "main.py")
        if not os.path.exists(main_py_path) and py_files:
            os.rename(os.path.join(app_path, py_files[0]), main_py_path)
        elif not py_files:
            return jsonify({"status": "error", "message": "No Python script found."}), 400

        create_venv_if_missing(venv_path)
        req_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(req_path):
            try:
                install_requirements(venv_path, req_path, cwd=app_path)
            except subprocess.CalledProcessError as e:
                return jsonify({"status": "error", "message": f"Dependency install failed: {e}"}), 500

    if new_image_file and new_image_file.filename:
        try:
            img_filename = f"{folder_name}_{google_id}.png"
            image_save_path = os.path.join("static/images", img_filename)
            if os.path.exists(image_save_path):
                os.remove(image_save_path)
            new_image_file.save(image_save_path)
        except Exception as e:
            print(f"⚠️ Could not save new image: {e}")

    update_button_metadata(google_id, folder_name, new_button_name)

    return jsonify({"status": "success", "message": "App updated successfully"})

@bot_bp.route("/delete/<folder_name>", methods=["POST"])
def delete_app(folder_name):
    if "google_id" not in session:
        # If not logged in, return 401 Unauthorized
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    google_id = session["google_id"]
    user_id = session.get("user_id")

    if not user_id:
         # Should not happen if google_id is present, but good practice
         return jsonify({"status": "error", "message": "User session error"}), 400

    # Get user-specific paths
    base_path, script_dir, _ = get_user_paths(google_id)
    app_path = os.path.join(script_dir, folder_name)

    # Check if the app directory exists before attempting deletion
    app_folder_exists = os.path.exists(app_path) and os.path.isdir(app_path)

    try:
        folder_deleted = False
        if app_folder_exists:
            # 1. Delete the app folder
            shutil.rmtree(app_path)
            folder_deleted = True # Mark folder as deleted

        # 2. Delete the app from the database regardless of folder status
        # (in case the folder was manually deleted but DB entry remains)
        db_deleted = delete_app_from_db(user_id, folder_name)

        if db_deleted:
            # Re-register apps only if DB deletion was successful
            try:
                from app import register_all_apps
                register_all_apps()
            except Exception as reg_err:
                 print(f"⚠️ Error re-registering apps after delete: {reg_err}")
                 # Don't fail the whole delete operation, just log the warning

            return jsonify({"status": "success", "message": f"App '{folder_name}' deleted successfully."}), 200
        elif folder_deleted:
             # Folder was deleted, but DB entry wasn't (or didn't exist)
             # This might be okay if the DB entry was already gone
             print(f"⚠️ App folder '{folder_name}' deleted, but no corresponding DB entry found or DB delete failed.")
             return jsonify({"status": "warning", "message": f"App folder '{folder_name}' deleted, but database entry issue occurred (check logs)."}), 200 # Still return success to user, but log warning
        else:
             # Neither folder existed nor DB entry was deleted
             return jsonify({"status": "error", "message": f"App '{folder_name}' not found or could not be deleted."}), 404


    except OSError as e:
        # Error during folder deletion
        print(f"❌ Error deleting folder {app_path}: {e}")
        # If DB deletion also failed or wasn't attempted, report folder error
        return jsonify({"status": "error", "message": f"Failed to delete app folder: {e}"}), 500
    except Exception as e:
        # Catch other potential errors (e.g., DB connection issues if not handled in delete_app_from_db)
        print(f"❌ Error deleting app {folder_name}: {e}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500