"""
Saathi AI Backend - Main Application
Updated with Community Safety Network features
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import routes
from app.routes import auth, users, community
from app.routes.emergency_updated import router as emergency_router

# Import services for health check
from app.services.supabase_service import supabase_service
from app.services.fcm_service import fcm_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Saathi AI Backend...")
    logger.info(f"  - Supabase configured: {supabase_service.is_configured()}")
    logger.info(f"  - FCM configured: {fcm_service.is_configured()}")
    yield
    # Shutdown
    logger.info("👋 Shutting down Saathi AI Backend...")


# Create FastAPI app
app = FastAPI(
    title="Saathi AI API",
    description="Emergency SOS and Community Safety Network API",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(community.router)
app.include_router(emergency_router)

# Also include your existing routes if they exist
# Uncomment and adjust these based on your existing code:
# from app.routes.query import router as query_router
# app.include_router(query_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Saathi AI API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Emergency SOS",
            "Community Safety Network",
            "Magic Link Authentication"
        ]
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "services": {
            "supabase": {
                "configured": supabase_service.is_configured(),
                "status": "connected" if supabase_service.is_configured() else "not configured"
            },
            "fcm": {
                "configured": fcm_service.is_configured(),
                "status": "ready" if fcm_service.is_configured() else "not configured"
            }
        },
        "environment": os.getenv("ENVIRONMENT", "development")
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error"
        }
    )


# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
