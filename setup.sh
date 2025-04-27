#!/bin/bash

echo "🔧 Checking virtual environment..."

# Step 1: Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment at ./venv"
    python3 -m venv venv

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment. Please ensure python3-venv is installed."
        echo "   Try: sudo apt install python3-venv"
        exit 1
    fi
fi

# Step 2: Activate the virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "🚀 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment activation script not found at venv/bin/activate"
    exit 1
fi

# Step 3: Install required packages from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📥 Installing packages from requirements.txt..."
    pip install --upgrade pip --quiet

    # You can suppress root warnings explicitly if needed
    pip install -r requirements.txt --root-user-action=ignore
    if [ $? -ne 0 ]; then
        echo "⚠️ Some packages may have failed to install. Check output above."
    else
        echo "✅ All packages installed successfully."
    fi
else
    echo "❌ requirements.txt not found in current directory: $(pwd)"
    exit 1
fi

# Final confirmation
echo "✅ Environment setup complete."