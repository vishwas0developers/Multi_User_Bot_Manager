#!/bin/bash

echo "🔋 Activating virtual environment..."

# Activate venv from the same directory as this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

# Run Flask app (assumes app.py is the entry point)
echo "🚀 Running Flask app..."
python app.py
