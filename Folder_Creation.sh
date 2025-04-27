#!/bin/bash

echo '🔧 Creating Flask Bot Manager folder structure...'

# Step 1: Get script base directory
BASE_DIR=$(dirname "$(realpath "$0")")
echo "📁 Working inside: $BASE_DIR"
cd "$BASE_DIR" || { echo '❌ Failed to switch directory.'; exit 1; }

# Step 2: Create directories
mkdir -p app
mkdir -p config
mkdir -p managed_bots
mkdir -p logs
mkdir -p migrations
mkdir -p app/routes
mkdir -p app/services
mkdir -p app/templates
mkdir -p app/templates/errors
mkdir -p app/static
mkdir -p app/static/css
mkdir -p app/static/js
mkdir -p app/static/images

# Step 3: Create empty placeholder files if not exist
[ -f ".env" ] || touch ".env"
[ -f ".flaskenv" ] || touch ".flaskenv"
[ -f ".gitignore" ] || touch ".gitignore"
[ -f "requirements.txt" ] || touch "requirements.txt"
[ -f "run.py" ] || touch "run.py"
[ -f "wsgi.py" ] || touch "wsgi.py"
[ -f "README.md" ] || touch "README.md"
[ -f "config/__init__.py" ] || touch "config/__init__.py"
[ -f "config/settings.py" ] || touch "config/settings.py"
[ -f "app/__init__.py" ] || touch "app/__init__.py"
[ -f "app/models.py" ] || touch "app/models.py"
[ -f "app/forms.py" ] || touch "app/forms.py"
[ -f "app/routes/__init__.py" ] || touch "app/routes/__init__.py"
[ -f "app/routes/main.py" ] || touch "app/routes/main.py"
[ -f "app/routes/bots.py" ] || touch "app/routes/bots.py"
[ -f "app/routes/api.py" ] || touch "app/routes/api.py"
[ -f "app/services/__init__.py" ] || touch "app/services/__init__.py"
[ -f "app/services/auth.py" ] || touch "app/services/auth.py"
[ -f "app/services/bot_management.py" ] || touch "app/services/bot_management.py"
[ -f "app/services/process_control.py" ] || touch "app/services/process_control.py"
[ -f "app/services/proxy_service.py" ] || touch "app/services/proxy_service.py"
[ -f "app/templates/base.html" ] || touch "app/templates/base.html"
[ -f "app/templates/index.html" ] || touch "app/templates/index.html"
[ -f "app/templates/login.html" ] || touch "app/templates/login.html"
[ -f "app/templates/_bot_card.html" ] || touch "app/templates/_bot_card.html"
[ -f "app/templates/errors/404.html" ] || touch "app/templates/errors/404.html"
[ -f "app/templates/errors/500.html" ] || touch "app/templates/errors/500.html"
[ -f "app/static/css/style.css" ] || touch "app/static/css/style.css"
[ -f "app/static/js/app.js" ] || touch "app/static/js/app.js"
[ -f "app/static/images/default_bot_icon.png" ] || touch "app/static/images/default_bot_icon.png"

# Step 4: Add content to key files if empty

# .gitignore
if [ ! -s ".gitignore" ]; then
cat <<EOF > .gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environment
venv/
managed_bots/*/venv/
.venv
ENV/
env/
VENV/
venv.bak/

# Environment variables
.env
.env.*
!.env.example

# Instance folder
instance/

# Log files
logs/
*.log

# Database files
*.db
*.sqlite3

# OS generated files
.DS_Store
Thumbs.db
EOF
echo "[+] .gitignore updated"
fi

# requirements.txt
if [ ! -s "requirements.txt" ]; then
cat <<EOF > requirements.txt
Flask==2.3.3
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.2.1
Flask-Login==0.6.3
Flask-Migrate==4.0.7
python-dotenv==1.0.1
requests==2.31.0
uv==0.1.33
SQLAlchemy==2.0.29
WTForms==3.1.2
Werkzeug==3.0.1
gunicorn==22.0.0
psutil==5.9.8
EOF
echo "[+] requirements.txt updated"
fi

# Final notes
echo ""
echo "✅ Structure created. Next steps:"
echo "1. python3 -m venv venv"
echo "2. source venv/bin/activate"
echo "3. pip install -r requirements.txt"
echo "4. flask run"
