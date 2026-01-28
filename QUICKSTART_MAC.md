# 🚀 Quick Start Guide for Mac

## Prerequisites Check

Open Terminal and verify you have Python 3.8+:
```bash
python3 --version
```

If not installed, install via Homebrew:
```bash
brew install python3
```

## Step-by-Step Setup

### 1. Navigate to project directory

```bash
cd ~/path/to/saathi-backend
```

### 2. Run automated setup

```bash
./setup.sh
```

This will:
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Create .env file from template

### 3. Add your API keys

Open the .env file in VSCode:
```bash
code .env
```

Or use nano:
```bash
nano .env
```

Replace the placeholder values with your actual API keys:

```env
GEMINI_API_KEY=AIza...your_actual_key
GROQ_API_KEY=gsk_...your_actual_key
GOOGLE_SEARCH_API_KEY=your_key_here
GOOGLE_SEARCH_ENGINE_ID=your_id_here
```

**Getting API Keys:**
- **Gemini**: Visit https://aistudio.google.com/app/apikey
- **Groq**: Visit https://console.groq.com/keys
- **Google Search** (optional): https://developers.google.com/custom-search

Save and close the file (Ctrl+X, then Y, then Enter if using nano).

### 4. Start the server

```bash
./run.sh
```

You should see:
```
✅ Starting server at http://localhost:8000
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Test the API

Open a new Terminal window and run:

```bash
# Simple health check
curl http://localhost:8000/

# Detailed health check
curl http://localhost:8000/health

# Test a query
curl -X POST http://localhost:8000/api/query \
  -F "text=Hello Saathi, introduce yourself"
```

Or visit in your browser:
- **API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Opening in VSCode

```bash
# Open entire project
code .

# Or just the app folder
code app/
```

## Troubleshooting

### "Permission denied" when running scripts
```bash
chmod +x setup.sh run.sh
```

### "command not found: python3"
Install Python via Homebrew:
```bash
brew install python3
```

### "Module not found" errors
Make sure virtual environment is activated:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port 8000 already in use
Kill the process:
```bash
lsof -ti:8000 | xargs kill -9
```

Or change port in .env:
```env
PORT=8001
```

### Cannot connect to API from React Native
Make sure:
1. Server is running
2. You're using correct URL (not localhost if testing on device)
3. CORS is enabled (already configured)

## Next Steps

Once backend is running:

1. ✅ Test all endpoints in browser (http://localhost:8000/docs)
2. 📱 Create React Native app
3. 🔗 Connect app to backend
4. 🧪 Test with real audio/images

## VSCode Extensions (Recommended)

Install these for better development experience:
- Python (by Microsoft)
- Pylance (by Microsoft)
- REST Client (for testing APIs)
- Python Environment Manager

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install new package
pip install package-name
pip freeze > requirements.txt

# Run tests
python tests/test_api.py

# Check code formatting
black app/

# View logs
# Logs appear in Terminal where you ran ./run.sh
```

## Development Workflow

1. Open project in VSCode: `code .`
2. Start server: `./run.sh`
3. Make code changes
4. Server auto-reloads (thanks to --reload flag)
5. Test in browser or with curl
6. Commit changes to git

## Ready to Deploy?

See `README.md` for deployment instructions to Render.com (free tier).

---

Need help? Check the main README.md or create an issue on GitHub.
