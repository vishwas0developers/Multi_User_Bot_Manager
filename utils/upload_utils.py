import os
import subprocess
# Import get_plan_limit and potentially remove get_db if no longer needed here
from utils.db_utils import get_db, get_user_id, get_user_plan, get_plan_limit
import zipfile
from werkzeug.utils import secure_filename
# Removed save_uploaded_app as it's handled in routes
# from utils.db_utils import save_uploaded_app
import platform
import sys

# Get base directory for a user
def get_user_paths(google_id):
    """Return user-specific base_path, scripts_dir, venv_path."""
    # Dynamically determine the project root directory (assuming utils is one level down)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # Define the base path for user apps within the 'apps' folder
    base_apps_path = os.path.join(project_root, "apps", str(google_id))
    # Define a separate path for temporary uploads if needed, or use a general temp location
    temp_upload_path = os.path.join(project_root, "uploads", str(google_id)) # Temporary storage during upload

    scripts_dir = base_apps_path  # Final destination for app scripts
    venv_path = os.path.join(scripts_dir, "venv") # venv inside the app's folder

    # Ensure both directories exist
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(temp_upload_path, exist_ok=True) # Ensure temp upload dir exists

    # Return the final app path, the temporary upload path, and the venv path
    return temp_upload_path, scripts_dir, venv_path

# Check if user can upload more apps based on their plan
def is_upload_allowed(user_id, plan):
    """Checks if the user can upload a new app based on their plan limit."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    # Count bots associated with the user_id
    cursor.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    count = result["count"] if result else 0
    cursor.close()
    conn.close()

    # Get the limit using the helper function
    limit = get_plan_limit(plan)

    print(f"User {user_id} (Plan: {plan}): App count = {count}, Limit = {limit}") # Debugging info

    # Check against infinity for gold plan explicitly if needed,
    # otherwise standard comparison works for float('inf')
    return count < limit

# Create virtual environment if it doesn't exist
def create_venv_if_missing(venv_path):
    if not os.path.exists(venv_path):
        # Change 'python3' to 'python' for Windows compatibility
        subprocess.run(["python", "-m", "venv", venv_path], check=True)
        print(f"✅ Virtualenv created at {venv_path}")

# Install requirements.txt inside user's venv
import subprocess
import os
import platform
import sys # sys मॉड्यूल इम्पोर्ट करें

def install_requirements(venv_path, requirements_path, cwd=None):
    """
    Installs packages from a requirements file into the specified virtual environment.

    Args:
        venv_path (str): The path to the virtual environment.
        requirements_path (str): The path to the requirements.txt file.
        cwd (str, optional): The working directory for the subprocess. Defaults to None.
    """
    if not os.path.exists(requirements_path):
        print(f"ℹ️ Requirements file not found at {requirements_path}, skipping installation.")
        return

    if not os.path.exists(venv_path):
        print(f"❌ Virtual environment not found at {venv_path}. Cannot install requirements.")
        # You might want to raise an exception here or handle it differently
        raise FileNotFoundError(f"Venv path does not exist: {venv_path}")

    print(f"⏳ Installing requirements from {requirements_path} into {venv_path}...")

    # Determine the correct path to the python executable within the venv
    if platform.system() == "Windows":
        python_executable = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        python_executable = os.path.join(venv_path, "bin", "python")

    if not os.path.exists(python_executable):
         print(f"❌ Python executable not found in venv: {python_executable}")
         # Fallback or raise error - maybe venv creation failed?
         # Trying system python as a last resort (less ideal)
         # python_executable = sys.executable # Less ideal, might install globally if venv broken
         raise FileNotFoundError(f"Python executable missing in venv: {python_executable}")


    try:
        # Use the venv's python to run pip
        command = [
            python_executable,
            "-m", "pip", "install",
            "-r", requirements_path,
            "--log", os.path.join(os.path.dirname(venv_path), f"{os.path.basename(venv_path)}_pip_install.log") # Log output
            # Add other pip options if needed, e.g., --no-cache-dir
        ]
        subprocess.run(command, check=True, cwd=cwd, capture_output=True, text=True) # Use capture_output and text=True
        print(f"✅ Successfully installed requirements into {venv_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements into {venv_path}.")
        print(f"Error output:\n{e.stderr}")
        # Re-raise the exception so the calling function knows about the failure
        raise e
    except FileNotFoundError:
         print(f"❌ Error: '{python_executable}' or 'pip' not found. Ensure the virtual environment is correctly set up.")
         raise # Re-raise the error


# Save uploaded files (This function might not need changes if routes/bot_manager.py handles paths correctly)
# Review routes/bot_manager.py upload_app function to ensure it uses the returned paths correctly.
# The second returned path from get_user_paths (scripts_dir) is the final destination.
def save_uploaded_files(zip_file, image, button_name, google_id, user_id):
    # This function seems less relevant now as the main logic is in routes/bot_manager.py
    # Keeping it for reference, but the primary changes are in get_user_paths and potentially upload_app route.
    temp_path, final_app_path_base, _ = get_user_paths(google_id) # Get the final base path

    folder_name = secure_filename(button_name.replace(' ', '_'))
    app_folder = os.path.join(final_app_path_base, folder_name) # Destination is within apps/<google_id>/<folder_name>

    os.makedirs(app_folder, exist_ok=True)

    # --- Logic below should ideally be in the route handler ---
    # Save and Extract ZIP (Example - actual logic is likely in the route)
    # temp_zip_location = os.path.join(temp_path, f"{folder_name}.zip")
    # zip_file.save(temp_zip_location)
    #
    # with zipfile.ZipFile(temp_zip_location, 'r') as zip_ref:
    #     zip_ref.extractall(app_folder) # Extract directly to final destination
    #
    # os.remove(temp_zip_location) # Remove temp zip

    # Save Image (Example)
    image_url = "/static/images/default-icon.png" # Default
    if image:
        # Image should likely be saved within the app_folder or a shared static location referenced correctly
        image_filename = f"{folder_name}_icon.png" # Or just icon.png
        image_path = os.path.join(app_folder, image_filename)
        image.save(image_path)
        # The URL needs to be accessible. If apps folder isn't served directly,
        # saving to static/user_images/<google_id>/... might be better.
        # For now, assuming a route will handle serving files from 'apps' if needed, or adjust save location.
        # This URL structure might need rethinking based on how files are served.
        image_url = f"/apps/{google_id}/{folder_name}/{image_filename}" # Placeholder URL
