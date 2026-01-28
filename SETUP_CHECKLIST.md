# ✅ Saathi Backend Setup Checklist

## Before You Start

- [ ] Mac with macOS 10.14 or later
- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] VSCode installed (optional but recommended)
- [ ] Terminal/command line access
- [ ] Internet connection

## API Keys Needed

- [ ] **Gemini API Key** 
  - Get from: https://aistudio.google.com/app/apikey
  - Free tier: 1,500 requests/day
  - ⚠️ REQUIRED for MVP

- [ ] **Groq API Key**
  - Get from: https://console.groq.com/keys
  - Free tier: 14,400 requests/day
  - ⚠️ REQUIRED for MVP

- [ ] **Google Custom Search API** (Optional for MVP)
  - Get from: https://developers.google.com/custom-search
  - Free tier: 100 queries/day
  - ✅ Nice to have, but not critical

## Setup Steps

### Part 1: Initial Setup

- [ ] Navigate to project directory in Terminal
  ```bash
  cd ~/path/to/saathi-backend
  ```

- [ ] Run setup script
  ```bash
  ./setup.sh
  ```

- [ ] Verify virtual environment created
  - Check that `venv/` folder exists

- [ ] Verify dependencies installed
  - No error messages during setup

### Part 2: Configuration

- [ ] Open .env file
  ```bash
  code .env
  # or
  nano .env
  ```

- [ ] Add Gemini API key
  ```
  GEMINI_API_KEY=AIza...
  ```

- [ ] Add Groq API key
  ```
  GROQ_API_KEY=gsk_...
  ```

- [ ] (Optional) Add Google Search credentials
  ```
  GOOGLE_SEARCH_API_KEY=...
  GOOGLE_SEARCH_ENGINE_ID=...
  ```

- [ ] Save and close .env file

### Part 3: First Run

- [ ] Start the server
  ```bash
  ./run.sh
  ```

- [ ] Verify server starts without errors
  - Look for: "Uvicorn running on http://0.0.0.0:8000"

- [ ] Keep this Terminal window open

- [ ] Open new Terminal window for testing

### Part 4: Testing

- [ ] Test health check
  ```bash
  curl http://localhost:8000/
  ```
  Expected: `{"service": "Saathi API", "status": "healthy", ...}`

- [ ] Test detailed health
  ```bash
  curl http://localhost:8000/health
  ```
  Expected: Shows API key configuration status

- [ ] Test text query
  ```bash
  curl -X POST http://localhost:8000/api/query \
    -F "text=Hello Saathi"
  ```
  Expected: JSON response with AI-generated text

- [ ] Open API docs in browser
  - Visit: http://localhost:8000/docs
  - Should see interactive API documentation

- [ ] Run test suite
  ```bash
  python tests/test_api.py
  ```
  Expected: All tests pass ✅

### Part 5: VSCode Setup (Optional)

- [ ] Open project in VSCode
  ```bash
  code .
  ```

- [ ] Install recommended extensions
  - Python (by Microsoft)
  - Pylance (by Microsoft)

- [ ] Select Python interpreter
  - Cmd+Shift+P → "Python: Select Interpreter"
  - Choose: `./venv/bin/python`

## Verification

### ✅ Backend is working if:

1. Server starts without errors
2. Health check returns "healthy" status
3. Text query returns AI response
4. API docs page loads (http://localhost:8000/docs)
5. Test suite passes

### ⚠️ Common Issues

**"Module not found" error:**
- Solution: Make sure virtual environment is activated
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**"API key not found" error:**
- Solution: Check .env file has correct keys with no extra spaces

**"Port already in use":**
- Solution: Kill existing process or change port
  ```bash
  lsof -ti:8000 | xargs kill -9
  ```

**Server starts but queries fail:**
- Check API keys are valid (no typos)
- Check internet connection
- Check API key quotas not exceeded

## Next Steps

Once all items are checked:

- [ ] Backend is fully operational ✅
- [ ] Ready to build React Native app
- [ ] Can start testing API endpoints
- [ ] Can proceed with frontend development

## Testing Checklist

Before moving to frontend:

- [ ] Text-only query works
- [ ] Image upload and analysis works
- [ ] Audio transcription works
- [ ] Combined audio + image query works
- [ ] Error handling works (invalid inputs)
- [ ] Response times are reasonable (<5 seconds)

## Documentation

- [ ] Read README.md for detailed documentation
- [ ] Read QUICKSTART_MAC.md for Mac-specific tips
- [ ] Import Postman collection for easy testing
- [ ] Bookmark API docs: http://localhost:8000/docs

## Ready for Production?

Before deploying to Render.com:

- [ ] All tests passing
- [ ] API keys working
- [ ] No security issues (don't commit .env!)
- [ ] .gitignore configured correctly
- [ ] README.md updated with your info

---

## Summary

**What You Built:**
- ✅ FastAPI backend server
- ✅ Gemini AI integration (vision + text)
- ✅ Groq speech-to-text
- ✅ Google Custom Search (optional)
- ✅ Image processing pipeline
- ✅ RESTful API endpoints
- ✅ Complete error handling
- ✅ Auto-reloading dev server

**What's Next:**
1. Build React Native app
2. Add screen capture in app
3. Add wake word detection
4. Connect app to this backend
5. Test end-to-end flow
6. Deploy to cloud (Render.com)

**Time Investment:**
- Setup: 15-30 minutes
- First successful test: 5 minutes
- Understanding codebase: 1-2 hours
- Building frontend: 1-2 weeks

You're now ready to build the mobile app! 🚀
