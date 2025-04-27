import os
import sys
import importlib.util
import shutil
import subprocess
import json
import zipfile
import psutil
import platform
from flask import Flask, render_template, redirect, url_for, session
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from dotenv import load_dotenv
from flask import send_from_directory
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.contact_routes import contact_bp
from routes.bot_manager import bot_bp
from auth_google import auth_bp, init_oauth
from utils.db_utils import get_all_users
from utils.upload_utils import get_user_paths

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

init_oauth(app)

app.register_blueprint(user_bp, url_prefix="/user")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(contact_bp, url_prefix="/contact")
app.register_blueprint(bot_bp, url_prefix="/bot")
app.register_blueprint(auth_bp)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
STATIC_IMAGE_FOLDER = os.path.join(BASE_DIR, "static", "images")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_IMAGE_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def register_all_apps():
    from importlib.util import spec_from_file_location, module_from_spec
    from importlib import invalidate_caches

    mapping = {}

    all_users = get_all_users()

    for user in all_users:
        google_id = user["google_id"]
        user_id = str(user["id"])
        base_path, script_dir, venv_path = get_user_paths(google_id)

        if not os.path.isdir(script_dir):
            continue

        for folder in os.listdir(script_dir):
            app_dir = os.path.join(script_dir, folder)
            main_file = os.path.join(app_dir, "main.py")

            if os.path.isdir(app_dir) and os.path.exists(main_file):
                try:
                    invalidate_caches()
                    modname = f"{google_id}_{folder}_app"
                    spec = spec_from_file_location(modname, main_file)
                    if spec and spec.loader:
                        module = module_from_spec(spec)
                        sys.modules[modname] = module
                        spec.loader.exec_module(module)

                        if hasattr(module, "app"):
                            mount_path = f"/u/{user_id}/{folder}"
                            mapping[mount_path] = module.app
                            print(f"✅ Mounted: {mount_path}")
                        else:
                            print(f"⚠️ No app found in {main_file}")
                    else:
                        print(f"❌ Could not create spec for {main_file}")
                except Exception as e:
                    print(f"❌ Failed to load {folder} for user {user_id}: {e}")

    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, mapping)
    print("✅ All user apps registered successfully.")

@app.route("/")
def home():
    if "google_id" in session:
        return redirect(url_for("user_bp.dashboard"))
    if session.get("is_admin"):
        return redirect(url_for("admin_bp.admin_panel"))
    return redirect(url_for("auth_bp.login"))

@app.route("/admin")
def admin_login_page():
    if session.get("is_admin"):
        return redirect(url_for("admin_bp.admin_panel"))
    return redirect(url_for("user_bp.admin_login"))

register_all_apps()


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    # Set environment variable to exclude uploads directory from reloader
    os.environ['FLASK_RUN_EXCLUDE_PATTERNS'] = 'uploads/*'
    # Setting WERKZEUG_RUN_MAIN might also help with reloader stability on some systems
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'

    # Calculate extra_files for the reloader to watch
    extra_dirs = ['routes', 'utils', 'templates', 'static'] # Add other dirs you want to watch
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = os.path.join(dirname, filename)
                if os.path.isfile(filename):
                    extra_files.append(filename)

    # Run the app, removing the reloader_options argument
    app.run(debug=True, host='0.0.0.0', port=8090,
            extra_files=extra_files, # Keep watching your source files
            use_reloader=True) # Removed reloader_options
