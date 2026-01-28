"""
Configuration settings for Saathi Backend
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server Settings (optional)
    APP_NAME: str = "Saathi API"
    DEBUG: bool = False
    HOST: Optional[str] = "0.0.0.0"
    PORT: Optional[str] = "8000"
    CORS_ORIGINS: Optional[str] = "*"
    
    # AI API Keys
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    
    # Search API
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_ENGINE_ID: Optional[str] = None
    
    # Emergency Services (NEW)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None  # Format: +1234567890
    
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[str] = None  # Format: alerts@yourdomain.com
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in .env without validation errors


# Global settings instance
settings = Settings()