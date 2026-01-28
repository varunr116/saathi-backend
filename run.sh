#!/bin/bash

# Saathi Backend Startup Script
# Run this script to start the backend server

echo "🙏 Starting Saathi Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run: cp .env.example .env"
    echo "Then add your API keys to .env"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed!"
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

# Start the server
echo "✅ Starting server at http://localhost:8000"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
