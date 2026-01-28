"""
Saathi Backend - Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import routes
from app.routes.query import router as query_router
from app.routes.emergency import router as emergency_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Saathi AI Backend",
    description="AI-powered companion with screen analysis, recording, and emergency features",
    version="2.0.0"
)

# CORS middleware - allow all origins for development
# In production, restrict to your mobile app domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(query_router)
app.include_router(emergency_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Saathi AI Backend",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Screen Analysis",
            "Voice Processing",
            "Emergency SOS",
            "Location Tracking"
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    from app.config import settings
    from app.services.sms_service import sms_service
    from app.services.email_service import email_service
    
    return {
        "service": "Saathi AI",
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "sms": sms_service.enabled,
            "email": email_service.enabled,
            "groq_ai": bool(settings.GROQ_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
            "web_search": bool(settings.GOOGLE_SEARCH_API_KEY)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )