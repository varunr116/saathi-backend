# 🙏 Saathi Backend

AI-powered companion assistant backend built with FastAPI, Gemini AI, and Groq.

## Features

- 🎤 **Speech-to-Text**: Convert voice commands to text using Groq's Whisper
- 👁️ **Screen Analysis**: Understand what's on user's phone screen with Gemini Vision
- 🤖 **Intelligent Responses**: Context-aware AI responses with Gemini 2.0 Flash
- 🔍 **Web Search**: Research brands, products, and information with Google Custom Search
- 🚀 **Fast & Async**: Built with FastAPI for high performance

## Prerequisites

- Python 3.8 or higher
- macOS/Linux (for this setup guide)
- API Keys:
  - Gemini API Key (https://aistudio.google.com/app/apikey)
  - Groq API Key (https://console.groq.com/keys)
  - Google Custom Search API Key (optional, for web search)

## Quick Start

### 1. Clone/Navigate to project directory

```bash
cd saathi-backend
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup environment variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

Add your actual API keys:
```env
GEMINI_API_KEY=your_actual_gemini_key_here
GROQ_API_KEY=your_actual_groq_key_here
GOOGLE_SEARCH_API_KEY=your_search_key_here  # Optional
GOOGLE_SEARCH_ENGINE_ID=your_engine_id_here  # Optional
```

### 5. Run the server

```bash
# Using Python directly
python -m uvicorn app.main:app --reload

# Or using the main.py script
python app/main.py
```

The server will start at `http://localhost:8000`

## Testing the API

### 1. Check if server is running

```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "service": "Saathi API",
  "status": "healthy",
  "version": "1.0.0",
  "message": "Namaste! 🙏"
}
```

### 2. Test text query (no image)

```bash
curl -X POST http://localhost:8000/api/query \
  -F "text=What is Saathi?"
```

### 3. Test with image

```bash
# Save a test image first, then:
curl -X POST http://localhost:8000/api/query \
  -F "text=What do you see in this image?" \
  -F "image=@/path/to/your/screenshot.png"
```

### 4. Test audio transcription

```bash
curl -X POST http://localhost:8000/api/transcribe \
  -F "audio=@/path/to/your/audio.wav"
```

### 5. Interactive API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Main Endpoints

#### POST `/api/query`
Main endpoint for processing user queries with optional screen context.

**Parameters:**
- `audio` (file, optional): Audio file for voice query
- `image` (file, optional): Screenshot for context
- `text` (string, optional): Direct text query

**Response:**
```json
{
  "success": true,
  "query": "Tell me about this brand",
  "response": "Based on the screenshot, I can see...",
  "has_screen_context": true,
  "used_web_search": true
}
```

#### POST `/api/transcribe`
Transcribe audio to text.

**Parameters:**
- `audio` (file, required): Audio file

**Response:**
```json
{
  "success": true,
  "text": "transcribed text here"
}
```

#### POST `/api/analyze-screen`
Analyze screenshot without specific query.

**Parameters:**
- `image` (file, required): Screenshot

**Response:**
```json
{
  "success": true,
  "description": "This appears to be Instagram showing..."
}
```

## Project Structure

```
saathi-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── routes/
│   │   ├── __init__.py
│   │   └── query.py         # Query endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py    # Gemini AI integration
│   │   ├── groq_service.py      # Groq STT integration
│   │   └── search_service.py    # Google Search integration
│   └── utils/
│       ├── __init__.py
│       └── image_utils.py       # Image processing utilities
├── tests/
├── .env                     # Environment variables (create this)
├── .env.example            # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GROQ_API_KEY` | Yes | Groq API key for speech-to-text |
| `GOOGLE_SEARCH_API_KEY` | No | Google Custom Search API key |
| `GOOGLE_SEARCH_ENGINE_ID` | No | Google Search Engine ID |
| `HOST` | No | Server host (default: 0.0.0.0) |
| `PORT` | No | Server port (default: 8000) |
| `DEBUG` | No | Enable debug mode (default: True) |

## Getting API Keys

### Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key

### Groq API Key
1. Go to https://console.groq.com/keys
2. Sign up/login
3. Create new API key
4. Copy the key

### Google Custom Search (Optional)
1. Go to https://developers.google.com/custom-search/v1/introduction
2. Create a new search engine at https://cse.google.com/cse/create/new
3. Get API key from Google Cloud Console
4. Copy both API key and Search Engine ID

## Deployment

### Deploy to Render.com (Free Tier)

1. Create account at https://render.com
2. Create new "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in Render dashboard
6. Deploy!

Your API will be live at: `https://your-app-name.onrender.com`

## Development

### Install development dependencies

```bash
pip install pytest black flake8
```

### Run tests

```bash
pytest
```

### Format code

```bash
black app/
```

### Check code quality

```bash
flake8 app/
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
Make sure you're in the project root and virtual environment is activated.

### "API key not found"
Check that `.env` file exists and contains your API keys. Make sure there are no extra spaces.

### "CORS error from React Native"
Check that `CORS_ORIGINS=*` is set in `.env` file.

### Port already in use
Change the port in `.env` file or kill the process using:
```bash
lsof -ti:8000 | xargs kill -9
```

## Free Tier Limits

- **Gemini 2.0 Flash**: 1,500 requests/day (free)
- **Groq**: 14,400 requests/day (free)
- **Google Custom Search**: 100 queries/day (free)

For MVP testing with 5-10 users, free tiers are sufficient!

## Next Steps

1. ✅ Backend is ready
2. 📱 Build React Native app
3. 🔗 Connect app to this backend
4. 🎤 Add wake word detection in app
5. 📸 Add screen capture in app
6. 🚀 Test end-to-end flow

## Support

For issues or questions, check:
- FastAPI docs: https://fastapi.tiangolo.com/
- Gemini API docs: https://ai.google.dev/docs
- Groq docs: https://console.groq.com/docs

---

Built with ❤️ for Saathi - Your AI Companion
