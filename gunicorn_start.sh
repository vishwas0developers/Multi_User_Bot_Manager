#!/bin/bash
echo "🔋 Activating virtual environment..."
source /home/bot-ssh/htdocs/bot.online2study.in/venv/bin/activate

echo "🚀 Starting Gunicorn with UNIX socket..."
exec gunicorn app:app \
    --bind unix:/home/bot-ssh/htdocs/bot.online2study.in/flask_app.sock \
    --workers 3 \
    --access-logfile - \
    --error-logfile -
