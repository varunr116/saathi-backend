#!/bin/bash

# Saathi Backend Setup Script
# Run this script to set up the backend for the first time

echo "🙏 Saathi Backend - Initial Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Python 3.8 or higher is required"
    exit 1
fi
echo "✅ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create .env file
echo "Setting up environment variables..."
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists, skipping..."
else
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys!"
    echo ""
    echo "Get your API keys from:"
    echo "  - Gemini: https://aistudio.google.com/app/apikey"
    echo "  - Groq: https://console.groq.com/keys"
    echo ""
    echo "Run: nano .env"
    echo "or open .env in your text editor"
fi
echo ""

# Make run script executable
chmod +x run.sh

echo "=================================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Run: ./run.sh (to start the server)"
echo "3. Visit: http://localhost:8000/docs (to see API docs)"
echo ""
echo "For testing, run: python tests/test_api.py"
