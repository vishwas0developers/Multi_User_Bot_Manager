# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import os
import re
import html
import io
import json
import requests
import uuid
from bs4 import BeautifulSoup
import zipfile
import openpyxl

app = Flask(__name__)
app.secret_key = "super_secret_key" # Keep this for session management (flash messages)

# --- Configuration File for Auth Code ---
AUTH_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "auth_config.txt")

# --- Helper Functions for Auth Code ---
def load_auth_code():
    """Loads the auth code from the config file."""
    try:
        with open(AUTH_CONFIG_FILE, "r") as f:
            # Read the first line and strip any whitespace/newlines
            code = f.readline().strip()
            if not code:
                print("⚠️ Auth config file is empty.")
                return None
            return code
    except FileNotFoundError:
        print(f"⚠️ Auth config file not found: {AUTH_CONFIG_FILE}. Please create it or use the update feature.")
        return None
    except Exception as e:
        print(f"⚠️ Error loading auth code: {e}")
        return None

def save_auth_code(new_code):
    """Saves the new auth code to the config file."""
    try:
        with open(AUTH_CONFIG_FILE, "w") as f:
            f.write(new_code)
        print(f"✅ Auth code updated successfully in {AUTH_CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"⚠️ Error saving auth code: {e}")
        flash(f"Error saving auth code: {e}", "error")
        return False

# --- Custom Exception for Auth Errors ---
class AuthCodeRequiredError(Exception):
    """Custom exception for missing or invalid auth code during API calls."""
    pass

# --- Constants ---
X_Tb_Client = "web,1.2"
attempt_no = "1"
DEFAULT_FOLDER = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DEFAULT_FOLDER, exist_ok=True)


# --- Helper Functions (Sanitize, Download Image, Generate Excel/JSON, ZIP) ---
# Keep these functions exactly as they were in the previous version
# (sanitize_filename, download_image, generate_excel, generate_json,
#  create_zip_from_folder, create_master_zip, cleanup_downloads)

def sanitize_filename(filename):
    """Replaces unsupported characters in filenames with a space, preserving Hindi and alphanumeric characters."""
    import re
    sanitized = re.sub(r"[^\w\s\u0900-\u097F.-]", " ", filename) # Added hyphen and dot
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized if sanitized else "untitled"

def download_image(image_url, folder_path):
    """Downloads an image from any valid image_url and saves it in folder_path."""
    os.makedirs(folder_path, exist_ok=True)

    if not image_url or not isinstance(image_url, str):
         print(f"⚠️ Skipping invalid image URL (not a string or empty): {image_url}")
         return None

    if image_url.startswith("//"):
        image_url = "https:" + image_url
    elif not image_url.startswith(("http:", "https:")):
         # Handle potentially relative URLs if necessary, or skip them
         print(f"⚠️ Skipping potentially relative or invalid scheme image URL: {image_url}")
         return None

    try:
        # Generate filename, handle cases without proper extension or path
        parsed_url = requests.utils.urlparse(image_url)
        base = os.path.basename(parsed_url.path)
        filename, ext = os.path.splitext(base)

        if not ext: # If no extension in path, try to get one from Content-Type or make one up
            try:
                 # Perform HEAD request first to check Content-Type without downloading body
                 head_resp = requests.head(image_url, timeout=5, allow_redirects=True)
                 head_resp.raise_for_status()
                 content_type = head_resp.headers.get('Content-Type', '').split(';')[0]
                 mime_to_ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif', 'image/webp': '.webp', 'image/bmp': '.bmp'}
                 ext = mime_to_ext.get(content_type, '.img') # Default to .img if type unknown
            except requests.exceptions.RequestException as head_e:
                 print(f"⚠️ HEAD request failed for {image_url}: {head_e}. Making default filename.")
                 ext = '.img' # Default extension if HEAD fails

            # Create a filename if the path didn't provide one
            if not filename:
                 filename = uuid.uuid4().hex # Generate unique filename


        # Sanitize filename and ensure it's not too long (optional, but good practice)
        final_filename = sanitize_filename(filename + ext)
        if len(final_filename) > 100: # Limit filename length
            final_filename = final_filename[:95] + ext


        file_path = os.path.join(folder_path, final_filename)

        # Only proceed if it looks like an image extension
        valid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".img")
        if not final_filename.lower().endswith(valid_extensions):
            print(f"⚠️ Skipping non-image URL (invalid extension '{ext}'): {image_url}")
            return None

        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        # Double-check content type if possible (optional)
        # content_type = response.headers.get('Content-Type', '').split(';')[0]
        # if not content_type.startswith('image/'):
        #    print(f"⚠️ Skipping non-image Content-Type '{content_type}': {image_url}")
        #    return None

        with open(file_path, "wb") as f:
            f.write(response.content)

        print(f"✅ Downloaded: {image_url} as {final_filename}")
        return final_filename # Return the actual saved filename

    except requests.exceptions.MissingSchema:
         print(f"⚠️ Invalid URL (Missing Schema): {image_url}")
         return None
    except requests.exceptions.InvalidURL:
         print(f"⚠️ Invalid URL: {image_url}")
         return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error downloading image {image_url}: {e}")
        return None
    except Exception as e: # Catch other potential errors like filesystem issues
        print(f"⚠️ Unexpected error processing image {image_url}: {e}")
        return None


def generate_excel(data):
    """Generates Excel content (.xlsx) from the scraped data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Scraped Questions"

    max_options = max((len(item.get("options", [])) for item in data), default=4)
    option_headers = [f"Option {chr(65 + i)}" for i in range(max_options)]
    header = ["Question Number", "Section", "Question"] + option_headers + [
        "Answer",
        "Explanation",
        "Image Relative Path", # Changed header slightly
    ]
    ws.append(header)

    for item in data:
        opts = item.get("options", [])
        if len(opts) < max_options:
            opts += [""] * (max_options - len(opts))

        # Extract relative image paths from HTML for the 'Image Relative Path' column
        image_paths = []
        for field in [item.get("question", ""), item.get("explanation", "")] + opts:
             if field and isinstance(field, str):
                 try:
                     soup = BeautifulSoup(field, "html.parser")
                     for img_tag in soup.find_all("img"):
                          src = img_tag.get("src")
                          # We only want the relative paths we created (e.g., 'images/...')
                          if src and src.startswith("images/"):
                              if src not in image_paths: # Avoid duplicates
                                  image_paths.append(src)
                 except Exception as e:
                      print(f"⚠️ Error parsing HTML for image paths: {e}")


        row_data = [
            item.get("question_number", ""),
            item.get("section", ""),
            item.get("question", ""),
        ] + opts + [
            item.get("answer", ""),
            item.get("explanation", ""),
            ", ".join(image_paths), # Comma-separated list of relative paths
        ]
        ws.append(row_data)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()

def generate_json(data):
    """Generates JSON content from the scraped data."""
    # Ensure data contains the processed HTML with relative image paths
    return json.dumps(data, ensure_ascii=False, indent=4)

def create_zip_from_folder(folder_path):
    """Creates a ZIP archive of a folder and returns the file path."""
    if not os.path.isdir(folder_path):
        print(f"⚠️ Cannot create ZIP, folder not found: {folder_path}")
        return None

    # Make zip filename more specific, place it one level up (in DEFAULT_FOLDER)
    parent_folder = os.path.dirname(folder_path)
    base_folder_name = os.path.basename(parent_folder) # Get the test name folder
    zip_filename = f"{base_folder_name}_images.zip" # e.g., TestName_images.zip
    zip_path = os.path.join(DEFAULT_FOLDER, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # arcname should be relative to the folder being zipped (images folder)
                    arcname = os.path.relpath(file_path, start=folder_path)
                    zf.write(file_path, arcname=arcname)
        return zip_path
    except Exception as e:
        print(f"⚠️ Error creating zip file {zip_path}: {e}")
        return None

def create_master_zip(results):
    """Creates a master ZIP archive containing all test results (Excel, JSON, Images)."""
    master_zip_filename = f"all_tests_{uuid.uuid4().hex}.zip"
    master_zip_path = os.path.join(DEFAULT_FOLDER, master_zip_filename)

    with zipfile.ZipFile(master_zip_path, "w", zipfile.ZIP_DEFLATED) as mzip:
        for res in results:
            test_folder_name_in_zip = sanitize_filename(res["test_title"])

            # Add Excel file
            excel_file_path = res.get("excel_filename")
            if excel_file_path and os.path.exists(excel_file_path):
                 # Arcname should be TestName/TestName.xlsx
                 mzip.write(excel_file_path, arcname=os.path.join(test_folder_name_in_zip, os.path.basename(excel_file_path)))
            else:
                 print(f"⚠️ Master Zip: Excel file not found for {res['test_title']}: {excel_file_path}")

            # Add JSON file
            json_file_path = res.get("json_filename")
            if json_file_path and os.path.exists(json_file_path):
                 # Arcname should be TestName/TestName.json
                 mzip.write(json_file_path, arcname=os.path.join(test_folder_name_in_zip, os.path.basename(json_file_path)))
            else:
                print(f"⚠️ Master Zip: JSON file not found for {res['test_title']}: {json_file_path}")

            # Add the separate Image ZIP if available
            # We add the ZIP itself into the test-specific folder within the master zip
            image_zip_path = res.get("zip_path") # This is the path to TestName_images.zip
            if image_zip_path and os.path.exists(image_zip_path):
                 # Arcname should be TestName/TestName_images.zip
                 mzip.write(image_zip_path, arcname=os.path.join(test_folder_name_in_zip, os.path.basename(image_zip_path)))
            # else: No warning needed if simply no images

    return master_zip_path


def cleanup_downloads():
    """Deletes all files and folders inside the 'downloads' folder before scraping."""
    # (Keep this function as it was)
    if os.path.exists(DEFAULT_FOLDER):
        for item in os.listdir(DEFAULT_FOLDER):
            # Skip the auth config file if it's accidentally placed inside downloads
            if item == os.path.basename(AUTH_CONFIG_FILE):
                continue
            item_path = os.path.join(DEFAULT_FOLDER, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    import shutil
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"⚠️ Error deleting {item_path}: {e}")
        print("✅ Download cleanup complete.")
    else:
        print("⚠️ No downloads folder found. Skipping cleanup.")

# --- API Scraping Functions ---
def scrape_test(api_url, language, auth_code):
    """Fetches test data from the Testbook API. Requires auth_code."""
    if not auth_code:
        raise AuthCodeRequiredError("Authentication code is missing.")

    # Ensure auth_code is part of the URL params
    if 'auth_code=' not in api_url:
         api_url += f"&auth_code={auth_code}"
    # If it might already be there, consider replacing it (more complex regex needed)
    # For simplicity, we assume it needs to be added or is correct

    try:
        response = requests.get(api_url, timeout=15) # Increased timeout slightly

        if response.status_code == 401:
            raise AuthCodeRequiredError("Authentication failed (401). Token likely expired or invalid.")
        
        response.raise_for_status() # Raise HTTPError for other bad responses (4xx, 5xx)

        json_data = response.json()
        if not json_data.get("success"):
            raise Exception(f"Test API response unsuccessful. Message: {json_data.get('msg', 'N/A')}")

        data = json_data.get("data", {})
        test_title = data.get("title", "Untitled Test")
        questions_data = []
        question_number = 1
        sections = data.get("sections", [])

        for section in sections:
            section_title = section.get("title", "Default Section")
            questions = section.get("questions", [])
            for q in questions:
                lang_data = q.get("hn", {}) if language == "Hindi" else q.get("en", {})
                if not lang_data or not lang_data.get("value", "").strip(): # Check if lang_data itself exists
                    lang_data = q.get("en", {}) # Fallback to English

                # Ensure lang_data is a dict before accessing keys
                if not isinstance(lang_data, dict):
                     print(f"⚠️ Skipping question due to unexpected language data format: {q.get('_id')}")
                     continue

                q_text = html.unescape(lang_data.get("value", ""))
                options = [html.unescape(opt.get("value", "")) for opt in lang_data.get("options", []) if isinstance(opt, dict)]

                questions_data.append(
                    {
                        "question_number": question_number,
                        "qid": q.get("_id", ""),
                        "section": section_title,
                        "question": q_text,
                        "options": options,
                        "answer": "",       # Populated later
                        "explanation": "", # Populated later
                        # "image" key removed, paths will be in question/explanation/options HTML
                    }
                )
                question_number += 1
        return test_title, questions_data

    except requests.exceptions.RequestException as e:
        # Catch specific request errors
        raise Exception(f"Network error fetching test data: {e}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON response from test API.")
    # AuthCodeRequiredError is raised explicitly above
    except Exception as e:
        # Catch any other unexpected errors
        # Avoid catching AuthCodeRequiredError here again
        if not isinstance(e, AuthCodeRequiredError):
            raise Exception(f"Unexpected error scraping test: {e}")
        else:
            raise e # Re-raise AuthCodeRequiredError


def scrape_answers(api_url, language, auth_code):
    """Fetches answer data from the Testbook API. Requires auth_code."""
    if not auth_code:
        raise AuthCodeRequiredError("Authentication code is missing.")

    # Ensure auth_code is part of the URL params
    if 'auth_code=' not in api_url:
         api_url += f"&auth_code={auth_code}"

    try:
        response = requests.get(api_url, timeout=15)

        if response.status_code == 401:
            raise AuthCodeRequiredError("Authentication failed (401) fetching answers. Token likely expired or invalid.")
        
        response.raise_for_status()

        json_data = response.json()
        if not json_data.get("success"):
            raise Exception(f"Answers API response unsuccessful. Message: {json_data.get('msg', 'N/A')}")

        answers_raw_data = json_data.get("data", {})
        lang_map = {"English": "en", "Hindi": "hn"}
        lang_key = lang_map.get(language, language.lower()) # Default to lower case if not found
        answers_mapping = {}

        for qid, details in answers_raw_data.items():
             if not isinstance(details, dict):
                  print(f"⚠️ Skipping answer for qid {qid} due to unexpected format.")
                  continue

             answer_index = details.get("correctOption", "") # Usually 0, 1, 2...
             sol_data = details.get("sol", {}).get(lang_key, {})

             # Ensure sol_data is a dict before accessing 'value'
             sol_unescaped = ""
             if isinstance(sol_data, dict):
                 sol_raw = sol_data.get("value", "")
                 sol_unescaped = html.unescape(sol_raw) if sol_raw else ""

             answers_mapping[qid] = {"answer_index": answer_index, "explanation": sol_unescaped}
        return answers_mapping

    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error fetching answers data: {e}")
    except json.JSONDecodeError:
        raise Exception("Failed to decode JSON response from answers API.")
    # AuthCodeRequiredError is raised explicitly above
    except Exception as e:
        if not isinstance(e, AuthCodeRequiredError):
             raise Exception(f"Unexpected error scraping answers: {e}")
        else:
             raise e # Re-raise AuthCodeRequiredError

# --- Flask Routes ---

@app.route("/", methods=["GET"])
def index_get():
    """Displays the main input form."""
    # Optionally check if auth code exists and flash a warning if not
    auth_code = load_auth_code()
    if not auth_code:
        flash("Auth code is missing. Please use 'Update Auth Code' if scraping fails.", "warning")
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def index_post():
    """Handles the scraping request."""
    # Clear old flash messages for this specific request processing
    session.pop('_flashes', None)

    # Load the current auth code
    current_auth_code = load_auth_code()
    if not current_auth_code:
        flash("Auth code is missing. Please update it.", "error")
        return redirect(url_for("update_auth_code_get")) # Redirect to update page

    # Cleanup downloads before starting
    cleanup_downloads()
    os.makedirs(DEFAULT_FOLDER, exist_ok=True)

    urls_input = request.form["urls"]
    language = request.form["language"]
    urls = [url.strip() for url in re.split(r"[,\n]+", urls_input) if url.strip()]

    if not urls:
        flash("Please enter at least one Testbook Test URL.", "error")
        return redirect(url_for("index_get")) # Back to form

    results = []
    any_error_occurred = False
    auth_error_occurred = False # Specific flag for auth errors

    for url in urls:
        try:
            print(f"🔄 Processing URL: {url}")
            match = re.search(r"testbook\.com/.*/tests/([^/?]+)", url) # Improved regex
            if not match:
                raise ValueError(f"Could not extract test ID from URL: {url}")

            test_id = match.group(1)
            # Construct API URLs (WITHOUT auth_code initially, it's added in scrape functions)
            base_api_url = f"https://api.testbook.com/api/v2/tests/{test_id}"
            test_api_url = f"{base_api_url}?X-Tb-Client={X_Tb_Client}&language={language}&attemptNo={attempt_no}"
            answers_api_url = f"{base_api_url}/answers?X-Tb-Client={X_Tb_Client}&language={language}&attemptNo={attempt_no}"

            # Scrape using the loaded auth code
            test_title, questions_data = scrape_test(test_api_url, language, current_auth_code)
            print(f"✅ Scraped test: {test_title}")
            answers_mapping = scrape_answers(answers_api_url, language, current_auth_code)
            print(f"✅ Scraped answers for: {test_title}")

            # --- Integrate Answers and Process Images ---
            folder_name_sanitized = sanitize_filename(test_title)
            test_specific_folder = os.path.join(DEFAULT_FOLDER, folder_name_sanitized)
            os.makedirs(test_specific_folder, exist_ok=True)
            image_folder = os.path.join(test_specific_folder, "images") # images subdir
            image_found = False

            for q in questions_data:
                qid = q.get("qid")
                # Determine Answer Text
                if qid and qid in answers_mapping:
                    answer_details = answers_mapping[qid]
                    answer_index = answer_details.get("answer_index")
                    if answer_index != "" and answer_index is not None:
                        try:
                            answer_idx_int = int(answer_index)
                            if 0 <= answer_idx_int < len(q["options"]):
                                q["answer"] = q["options"][answer_idx_int] # Use the option text
                            else:
                                q["answer"] = f"Invalid Option Index: {answer_index}"
                        except (ValueError, TypeError):
                            q["answer"] = f"Invalid Index Format: {answer_index}"
                    else:
                        q["answer"] = "N/A"
                    q["explanation"] = answer_details.get("explanation", "")
                else:
                     q["answer"] = "Answer Key Missing"
                     q["explanation"] = q.get("explanation", "") # Keep explanation if it somehow existed

                # Process images in Question, Explanation, Options
                relative_image_paths_in_q = [] # Track paths for this question

                # Process question and explanation directly
                for field in ["question", "explanation"]:
                    if q.get(field):
                        soup = BeautifulSoup(q[field], "html.parser")
                        img_tags = soup.find_all("img")
                        for img_tag in img_tags:
                            img_url = img_tag.get("src", "")
                            if img_url:
                                # Pass image_folder (absolute path) for download
                                local_img_filename = download_image(img_url, image_folder)
                                if local_img_filename:
                                    image_found = True
                                    # Update src to relative path (images/filename.ext)
                                    relative_img_path = os.path.join("images", local_img_filename).replace("\\", "/")
                                    img_tag["src"] = relative_img_path
                                    if relative_img_path not in relative_image_paths_in_q:
                                         relative_image_paths_in_q.append(relative_img_path)

                                else:
                                    img_tag.replace_with(f"[Image download failed: {img_url}]")
                        q[field] = str(soup) # Update with modified HTML

                # Process options
                updated_options = []
                for opt_html in q.get("options",[]):
                    soup = BeautifulSoup(opt_html, "html.parser")
                    img_tags = soup.find_all("img")
                    for img_tag in img_tags:
                        img_url = img_tag.get("src", "")
                        if img_url:
                            local_img_filename = download_image(img_url, image_folder)
                            if local_img_filename:
                                image_found = True
                                relative_img_path = os.path.join("images", local_img_filename).replace("\\", "/")
                                img_tag["src"] = relative_img_path
                                if relative_img_path not in relative_image_paths_in_q:
                                     relative_image_paths_in_q.append(relative_img_path)
                            else:
                                img_tag.replace_with(f"[Image download failed: {img_url}]")
                    updated_options.append(str(soup))
                q["options"] = updated_options
                # q["image_paths"] = relative_image_paths_in_q # Optionally store paths directly


            # --- Generate and Save Files ---
            excel_filename = os.path.join(test_specific_folder, folder_name_sanitized + ".xlsx")
            json_filename = os.path.join(test_specific_folder, folder_name_sanitized + ".json")

            excel_content = generate_excel(questions_data)
            json_content = generate_json(questions_data)

            with open(excel_filename, "wb") as f:
                f.write(excel_content)
            print(f"✅ Saved Excel: {excel_filename}")
            with open(json_filename, "w", encoding="utf-8") as f:
                f.write(json_content)
            print(f"✅ Saved JSON: {json_filename}")

            # Create Image ZIP (containing files from image_folder)
            images_zip_path = None
            if image_found and os.path.exists(image_folder) and any(os.listdir(image_folder)):
                 # Pass the specific image folder to zip
                images_zip_path = create_zip_from_folder(image_folder)
                if images_zip_path:
                    print(f"✅ Created Image ZIP: {images_zip_path}")
                else:
                    print(f"⚠️ Failed to create Image ZIP for: {image_folder}")


            results.append(
                {
                    "test_title": test_title,
                    "excel_filename": excel_filename, # Full path
                    "json_filename": json_filename,   # Full path
                    "zip_path": images_zip_path,      # Full path to the image zip
                    "test_folder_path": test_specific_folder # Full path
                }
            )

        except AuthCodeRequiredError as ae:
            any_error_occurred = True
            auth_error_occurred = True # Set the specific flag
            print(f"Auth Error: {ae}")
            flash(f"{ae} Please update the Auth Code.", "error")
            # Stop processing further URLs if auth fails for one
            break # Exit the loop

        except ValueError as ve: # Catch specific URL parsing errors
             any_error_occurred = True
             print(f"Value Error: {ve}")
             flash(f"Skipping URL '{url}': {ve}", "warning")
             continue # Skip to next URL

        except Exception as e:
            any_error_occurred = True
            print(f"❌ Error processing URL {url}: {e}")
            # Optionally add traceback: import traceback; print(traceback.format_exc())
            flash(f"Error processing URL {url}: {e}", "error")
            # Decide if you want to stop on general errors or continue
            # continue # Or break, depending on desired behavior
            continue


    # --- After the loop ---
    session["results"] = results # Save successful results to session

    if auth_error_occurred:
         # Redirect immediately to update page if auth failed
         return redirect(url_for('update_auth_code_get'))

    # Add general warning only if errors occurred AND no results were successful
    if any_error_occurred and not results:
        flash("⚠️ No tests were successfully processed. Check URLs and logs.", "warning")
        # Maybe redirect back to index if nothing worked at all?
        # return redirect(url_for('index_get'))

    # If loop finished (even with non-auth errors), go to results page
    return redirect(url_for("results"))


# --- Route for Updating Auth Code ---
@app.route("/update_auth", methods=["GET"])
def update_auth_code_get():
    """Displays the form to update the auth code."""
    return render_template("update_auth.html")

@app.route("/update_auth", methods=["POST"])
def update_auth_code_post():
    """Handles submission of the new API URL to extract the auth code."""
    api_url = request.form.get("api_url")
    if not api_url:
        flash("Please paste the API URL containing the new auth_code.", "error")
        return redirect(url_for("update_auth_code_get"))

    # Regex to find auth_code=... value
    match = re.search(r"auth_code=([^&]+)", api_url)
    if match:
        new_code = match.group(1)
        if save_auth_code(new_code):
             flash("Auth code updated successfully!", "success")
             # Redirect back to the main page after successful update
             return redirect(url_for("index_get"))
        else:
             # Error saving is flashed in save_auth_code
             return redirect(url_for("update_auth_code_get"))
    else:
        flash("Could not find 'auth_code=' parameter in the provided URL. Please paste the full, correct API URL.", "error")
        return redirect(url_for("update_auth_code_get"))


# --- Route for Displaying Results ---
@app.route("/results")
def results():
    """Displays results and download options."""
    # (This route remains largely the same as the previous version,
    #  ensure it uses the correct keys from the 'results' dict in session)
    results_data = session.get("results", [])
    processed_results = []

    if not results_data and not session.get('_flashes'): # Avoid showing "no results" if there's an error flash
         flash("No results found in session. Please start a new scrape.", "info")
         # Optional: redirect to index if absolutely no results and no flashes
         # return redirect(url_for('index_get'))


    for res in results_data:
        test_folder_path = res.get("test_folder_path")
        if not test_folder_path or not os.path.isdir(test_folder_path):
             print(f"⚠️ Results Page: Skipping result, test folder not found: {res.get('test_title')}")
             continue

        test_folder_name = os.path.basename(test_folder_path)

        # Image ZIP check
        res["image_available"] = res.get("zip_path") and os.path.exists(res["zip_path"])

        # Individual Complete ZIP Creation
        individual_zip_filename = f"{test_folder_name}_complete.zip"
        individual_zip_path = os.path.join(DEFAULT_FOLDER, individual_zip_filename)
        res["individual_zip_path"] = None # Default to None

        # Create individual zip if it doesn't exist
        # No need to recreate it every time the results page is loaded
        if not os.path.exists(individual_zip_path):
            try:
                with zipfile.ZipFile(individual_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Add Excel
                    excel_file_path = res.get("excel_filename")
                    if excel_file_path and os.path.exists(excel_file_path):
                        zipf.write(excel_file_path, arcname=os.path.basename(excel_file_path))
                    # Add JSON
                    json_file_path = res.get("json_filename")
                    if json_file_path and os.path.exists(json_file_path):
                        zipf.write(json_file_path, arcname=os.path.basename(json_file_path))
                    # Add Image ZIP
                    image_zip_path = res.get("zip_path")
                    if image_zip_path and os.path.exists(image_zip_path):
                         zipf.write(image_zip_path, arcname=os.path.basename(image_zip_path))
                res["individual_zip_path"] = individual_zip_path # Store path if created
                print(f"✅ Results Page: Created individual complete ZIP: {individual_zip_path}")
            except Exception as e:
                 print(f"⚠️ Results Page: Error creating individual zip {individual_zip_path}: {e}")
                 # Keep res["individual_zip_path"] as None
        else:
             res["individual_zip_path"] = individual_zip_path # Store path if already exists

        # Prepare relative paths for download links
        # Relative path for files *inside* the test-specific folder
        excel_rel_path = None
        if res.get("excel_filename") and os.path.exists(res["excel_filename"]):
             excel_rel_path = os.path.join(test_folder_name, os.path.basename(res["excel_filename"])).replace("\\","/")
             res["excel_download_path"] = excel_rel_path

        json_rel_path = None
        if res.get("json_filename") and os.path.exists(res["json_filename"]):
             json_rel_path = os.path.join(test_folder_name, os.path.basename(res["json_filename"])).replace("\\","/")
             res["json_download_path"] = json_rel_path

        # Relative path for ZIP files (which are directly in DEFAULT_FOLDER)
        image_zip_rel_path = None
        if res.get("zip_path") and os.path.exists(res["zip_path"]):
             image_zip_rel_path = os.path.basename(res["zip_path"])
             res["image_zip_download_path"] = image_zip_rel_path

        individual_zip_rel_path = None
        if res.get("individual_zip_path") and os.path.exists(res["individual_zip_path"]):
            individual_zip_rel_path = os.path.basename(res["individual_zip_path"])
            res["individual_zip_download_path"] = individual_zip_rel_path

        processed_results.append(res)

    master_zip_available = bool(processed_results)
    return render_template(
        "result.html",
        results=processed_results,
        master_zip_available=master_zip_available,
    )


# --- Download Routes ---
# These should work correctly with the paths generated in the /results route
@app.route("/download/<path:filepath>")
def download(filepath):
    """Serves individual files (Excel, JSON) using combined path."""
    full_path = os.path.join(DEFAULT_FOLDER, filepath)

    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(DEFAULT_FOLDER)):
        return "Forbidden", 403

    if os.path.exists(full_path) and os.path.isfile(full_path):
         print(f"⬇️ Serving file: {full_path}")
         return send_file(full_path, as_attachment=True)
    else:
        print(f"❌ File not found for download: {full_path}")
        flash(f"Download error: File not found at {filepath}", "error")
        return redirect(request.referrer or url_for('results')) # Go back or to results


@app.route("/download_zip/<filename>")
def download_zip(filename):
    """Serves ZIP files (Images ZIP, Complete ZIP) from the main download folder."""
    zip_path = os.path.join(DEFAULT_FOLDER, filename)

    # Security check
    if not os.path.abspath(zip_path).startswith(os.path.abspath(DEFAULT_FOLDER)):
         return "Forbidden", 403

    if os.path.exists(zip_path) and os.path.isfile(zip_path):
        print(f"⬇️ Serving ZIP: {zip_path}")
        return send_file(zip_path, as_attachment=True)
    else:
        print(f"❌ ZIP file not found: {zip_path}")
        flash(f"Download error: ZIP file not found: {filename}", "error")
        return redirect(request.referrer or url_for('results'))


@app.route("/download_master_zip")
def download_master_zip():
    """Generates and downloads a master ZIP with all files."""
    results = session.get("results", [])
    if not results:
        flash("No results found in session to create a master ZIP.", "warning")
        return redirect(url_for('results'))

    try:
        master_zip_path = create_master_zip(results)
        if master_zip_path and os.path.exists(master_zip_path):
             return send_file(master_zip_path, as_attachment=True, download_name="All_Tests_Scraped.zip")
        else:
             flash("Error: Master ZIP file could not be generated or found.", "error")
             print(f"❌ Master ZIP not found or not created at: {master_zip_path}")
             return redirect(url_for('results'))
    except Exception as e:
        flash(f"Error creating master zip: {e}", "error")
        print(f"❌ Error during master zip creation: {e}")
        # import traceback; print(traceback.format_exc())
        return redirect(url_for('results'))


# --- App Startup ---
if __name__ == "__main__":
    # Ensure downloads directory exists on startup
    os.makedirs(DEFAULT_FOLDER, exist_ok=True)
    # Check for auth code file on startup
    if not os.path.exists(AUTH_CONFIG_FILE):
        print(f"Auth code file '{AUTH_CONFIG_FILE}' not found. Creating empty file.")
        print("Scraping will fail until you update the auth code via the web interface.")
        open(AUTH_CONFIG_FILE, 'a').close() # Create empty file if it doesn't exist

    app.run(debug=True, host="0.0.0.0", port=5000)