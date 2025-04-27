@echo off
setlocal enabledelayedexpansion

:: Set the base directory for the project
set "BASE_DIR=%~dp0"
echo Creating project structure in: %BASE_DIR%

:: Check if base directory already exists
if exist "%BASE_DIR%" (
    echo WARNING: Directory "%BASE_DIR%" already exists.
    set /p "confirm=Do you want to continue and potentially overwrite structure? (y/N): "
    if /i not "!confirm!"=="y" (
        echo Aborting script.
        exit /b 1
    )
    echo Proceeding...
) else (
    mkdir "%BASE_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create base directory: %BASE_DIR%
        exit /b 1
    )
)

:: Change to the base directory
cd /d "%BASE_DIR%" || (
    echo ERROR: Failed to change directory to %BASE_DIR%
    exit /b 1
)

:: === Create Core Directories ===
echo --- Creating core directories ---
mkdir "app"
mkdir "config"
mkdir "managed_bots"
mkdir "logs"
mkdir "migrations"

:: === Create 'app' Subdirectories ===
echo --- Creating 'app' subdirectories ---
mkdir "app\routes"
mkdir "app\services"
mkdir "app\templates"
mkdir "app\templates\errors"
mkdir "app\static"
mkdir "app\static\css"
mkdir "app\static\js"
mkdir "app\static\images"

:: === Create Empty Placeholder Files ===
echo --- Creating placeholder files ---

:: Top Level Files
type NUL > ".env"              && echo [+] Created .env
type NUL > ".flaskenv"         && echo [+] Created .flaskenv
type NUL > ".gitignore"        && echo [+] Created .gitignore
type NUL > "requirements.txt"  && echo [+] Created requirements.txt
type NUL > "run.py"            && echo [+] Created run.py
type NUL > "wsgi.py"           && echo [+] Created wsgi.py
type NUL > "README.md"         && echo [+] Created README.md

:: Config Files
type NUL > "config\__init__.py" && echo [+] Created config\__init__.py
type NUL > "config\settings.py" && echo [+] Created config\settings.py

:: App Core Files
type NUL > "app\__init__.py"    && echo [+] Created app\__init__.py
type NUL > "app\models.py"      && echo [+] Created app\models.py
type NUL > "app\forms.py"       && echo [+] Created app\forms.py

:: App Routes Files
type NUL > "app\routes\__init__.py" && echo [+] Created app\routes\__init__.py
type NUL > "app\routes\main.py"     && echo [+] Created app\routes\main.py
type NUL > "app\routes\bots.py"     && echo [+] Created app\routes\bots.py
type NUL > "app\routes\api.py"      && echo [+] Created app\routes\api.py

:: App Services Files
type NUL > "app\services\__init__.py"         && echo [+] Created app\services\__init__.py
type NUL > "app\services\auth.py"             && echo [+] Created app\services\auth.py
type NUL > "app\services\bot_management.py"   && echo [+] Created app\services\bot_management.py
type NUL > "app\services\process_control.py"  && echo [+] Created app\services\process_control.py
type NUL > "app\services\proxy_service.py"    && echo [+] Created app\services\proxy_service.py

:: App Templates Files
type NUL > "app\templates\base.html"        && echo [+] Created app\templates\base.html
type NUL > "app\templates\index.html"       && echo [+] Created app\templates\index.html
type NUL > "app\templates\login.html"       && echo [+] Created app\templates\login.html
type NUL > "app\templates\_bot_card.html"   && echo [+] Created app\templates\_bot_card.html
type NUL > "app\templates\errors\404.html"  && echo [+] Created app\templates\errors\404.html
type NUL > "app\templates\errors\500.html"  && echo [+] Created app\templates\errors\500.html

:: App Static Files
type NUL > "app\static\css\style.css"       && echo [+] Created app\static\css\style.css
type NUL > "app\static\js\app.js"           && echo [+] Created app\static\js\app.js
:: Create an empty placeholder for the image - you should replace this with a real PNG later
type NUL > "app\static\images\default_bot_icon.png" && echo [+] Created app\static\images\default_bot_icon.png (Placeholder)

:: === Add Basic Content to Some Files ===
echo --- Adding basic content ---

:: .gitignore
(
    echo # Byte-compiled / optimized / DLL files
    echo __pycache__/
    echo *.py[cod]
    echo *$py.class
    echo.
    echo # Virtual environment
    echo venv/
    echo managed_bots/*/venv/
    echo .venv
    echo ENV/
    echo env/
    echo VENV/
    echo venv.bak/
    echo.
    echo # Environment variables
    echo .env
    echo .env.*
    echo !.env.example
    echo.
    echo # Instance folder
    echo instance/
    echo.
    echo # Log files
    echo logs/
    echo *.log
    echo.
    echo # Database files
    echo *.db
    echo *.sqlite3
    echo.
    echo # OS generated files
    echo .DS_Store
    echo Thumbs.db
) > ".gitignore" && echo [+] Added content to .gitignore

:: requirements.txt (Add essential manager dependencies)
(
    echo Flask==2.3.3
    echo Flask-SQLAlchemy==3.1.1
    echo Flask-WTF==1.2.1
    echo Flask-Login==0.6.3
    echo Flask-Migrate==4.0.7
    echo python-dotenv==1.0.1
    echo requests==2.31.0
    echo uv==0.1.33
    echo SQLAlchemy==2.0.29
    echo WTForms==3.1.2
    echo Werkzeug==3.0.1
    echo gunicorn==22.0.0
    echo psutil==5.9.8
) > "requirements.txt" && echo [+] Added content to requirements.txt

:: .flaskenv
(
    echo FLASK_APP=run.py
    echo FLASK_ENV=development
    echo # You might need FLASK_DEBUG=1 depending on your run setup
    echo # Specify DOTENV_PATH if your .env is not in the root
    echo # DOTENV_PATH=.env
) > ".flaskenv" && echo [+] Added content to .flaskenv

:: run.py (Basic app runner)
(
    echo from app import create_app
    echo from dotenv import load_dotenv
    echo import os
    echo.
    echo # Load environment variables from .env file
    echo load_dotenv()
    echo.
    echo app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    echo.
    echo if __name__ == '__main__':
    echo     # Use debug=True carefully in production
    echo     # Set host='0.0.0.0' to be accessible externally
    echo     # Consider using Flask's built-in server only for development
    echo     app.run(host='0.0.0.0', port=5000, debug=True)
) > "run.py" && echo [+] Added content to run.py

:: wsgi.py (Basic WSGI entry point)
(
    echo from app import create_app
    echo from dotenv import load_dotenv
    echo import os
    echo.
    echo load_dotenv()
    echo.
    echo application = create_app(os.getenv('FLASK_CONFIG') or 'production')
) > "wsgi.py" && echo [+] Added content to wsgi.py

:: app/__init__.py (Basic app factory structure)
(
    echo from flask import Flask
    echo from flask_sqlalchemy import SQLAlchemy
    echo from flask_login import LoginManager
    echo from flask_wtf.csrf import CSRFProtect
    echo from config import config # Import config dictionary
    echo import os
    echo import logging
    echo from logging.handlers import RotatingFileHandler
    echo.
    echo db = SQLAlchemy()
    echo login_manager = LoginManager()
    echo login_manager.login_view = 'main.login' # Adjust if using a different blueprint/endpoint name
    echo csrf = CSRFProtect()
    echo.
    echo def create_app(config_name='default'):
    echo     """Application factory"""
    echo     app = Flask(__name__)
    echo.
    echo     # Load configuration
    echo     app.config.from_object(config[config_name])
    echo     config[config_name].init_app(app)
    echo.
    echo     # Initialize extensions
    echo     db.init_app(app)
    echo     login_manager.init_app(app)
    echo     csrf.init_app(app)
    echo.
    echo     # Setup Logging
    echo     if not app.debug and not app.testing:
    echo         log_dir = app.config.get('LOGS_DIR', 'logs')
    echo         if not os.path.exists(log_dir):
    echo             os.makedirs(log_dir)
    echo         file_handler = RotatingFileHandler(
    echo             os.path.join(log_dir, 'app.log'),
    echo             maxBytes=10240, backupCount=10
    echo         )
    echo         file_handler.setFormatter(logging.Formatter(
    echo             '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    echo         ))
    echo         file_handler.setLevel(logging.INFO)
    echo         app.logger.addHandler(file_handler)
    echo         app.logger.setLevel(logging.INFO)
    echo         app.logger.info('Flask Bot Manager startup')
    echo.
    echo     # Register Blueprints
    echo     from .routes.main import main as main_blueprint
    echo     app.register_blueprint(main_blueprint)
    echo.
    echo     from .routes.bots import bots as bots_blueprint
    echo     app.register_blueprint(bots_blueprint, url_prefix='/bots') # Example prefix
    echo.
    echo     from .routes.api import api as api_blueprint
    echo     app.register_blueprint(api_blueprint, url_prefix='/api')
    echo.
    echo     # Add proxy route registration here later if needed directly on app
    echo     from .services.proxy_service import configure_proxy
    echo     configure_proxy(app) # Assuming proxy logic is configured here
    echo.
    echo     # Add error handlers
    echo     from .error_handlers import register_error_handlers # You'll need to create this file/function
    echo     register_error_handlers(app)
    echo.
    echo     return app
    echo.
    echo # You might need to create app/error_handlers.py
    echo # Example error_handlers.py content:
    echo # from flask import render_template
    echo # def register_error_handlers(app):
    echo #     @app.errorhandler(404)
    echo #     def page_not_found(e):
    echo #         return render_template('errors/404.html'), 404
    echo #     @app.errorhandler(500)
    echo #     def internal_server_error(e):
    echo #         return render_template('errors/500.html'), 500

) > "app\__init__.py" && echo [+] Added basic structure to app\__init__.py

echo.
echo ✅ Folder structure and basic files created successfully in %BASE_DIR%
echo.
echo --- Next Steps ---
echo 1. Create the manager's virtual environment: cd %BASE_DIR% ^& python -m venv venv (or use uv venv venv)
echo 2. Activate the environment: venv\Scripts\activate
echo 3. Install dependencies: pip install -r requirements.txt (or uv pip install -r requirements.txt)
echo 4. Install 'uv' if you haven't already (pip install uv)
echo 5. Configure database settings in config/settings.py and connection details in .env
echo 6. Initialize the database (e.g., using Flask-Migrate: flask db init, flask db migrate, flask db upgrade)
echo 7. Create an initial user if needed.
echo 8. Replace app\static\images\default_bot_icon.png with a real image file.
echo 9. Start developing the application logic in the created files.
echo 10. Run the development server: flask run

endlocal
pause