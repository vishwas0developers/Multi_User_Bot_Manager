#!/bin/bash

echo "🔋 Switching to bot-ssh user..."
sudo su - bot-ssh << 'EOF'
echo "📂 Moving into project directory..."
cd ~/htdocs/bot.online2study.in/

echo "🚀 Activating virtual environment..."
source venv/bin/activate

echo "🔄 Restarting Gunicorn manually..."
bash gunicorn_start.sh

echo "✅ Gunicorn started. Exiting bot-ssh user session..."
exit
EOF

echo "🛠️ Reloading systemctl daemon..."
sudo systemctl daemon-reload

echo "🛡️ Enabling botmanager service..."
sudo systemctl enable botmanager

echo "🔄 Restarting botmanager service..."
sudo systemctl restart botmanager

echo "🔍 Checking botmanager service status..."
sudo systemctl status botmanager --no-pager

echo "✅ Restart process completed successfully!"
