"""
Groq Service for Speech-to-Text using Whisper
"""
from groq import Groq
from typing import Dict, Any
import io
from app.config import settings


class GroqService:
    """Service for speech-to-text using Groq's Whisper API"""
    
    def __init__(self):
        """Initialize Groq client"""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        
    async def transcribe_audio(
        self, 
        audio_bytes: bytes, 
        filename: str = "audio.wav"
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Args:
            audio_bytes: Audio file bytes
            filename: Original filename (for format detection)
            
        Returns:
            Dict with transcription results
        """
        try:
            # Groq expects a file-like object
            audio_file = (filename, audio_bytes)
            
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=settings.GROQ_STT_MODEL,
                response_format="json",
                language="en",  # Can auto-detect Hindi/English
                temperature=0.0  # Most accurate transcription
            )
            
            return {
                "success": True,
                "text": transcription.text,
                "language": "auto-detected"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": None
            }
    
    async def transcribe_with_language(
        self,
        audio_bytes: bytes,
        language: str = "en",
        filename: str = "audio.wav"
    ) -> Dict[str, Any]:
        """
        Transcribe audio with specific language
        
        Args:
            audio_bytes: Audio file bytes
            language: ISO language code (en, hi, etc.)
            filename: Original filename
            
        Returns:
            Dict with transcription results
        """
        try:
            audio_file = (filename, audio_bytes)
            
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=settings.GROQ_STT_MODEL,
                response_format="json",
                language=language,
                temperature=0.0
            )
            
            return {
                "success": True,
                "text": transcription.text,
                "language": language
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": None
            }


# Singleton instance
groq_service = GroqService()
