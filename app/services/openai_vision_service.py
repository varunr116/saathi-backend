"""
OpenAI Vision Service for image analysis with AI-powered brand detection
"""
from openai import OpenAI
from PIL import Image
import base64
import io
import json
from typing import Dict, Any
from app.config import settings


class OpenAIVisionService:
    """Service for OpenAI GPT-4 Vision with intelligent analysis"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Cheaper alternative
        
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode()
    
    async def analyze_screen_with_query(
        self, 
        image: Image.Image, 
        query: str
    ) -> Dict[str, Any]:
        """
        AI-powered screenshot analysis with brand detection and research recommendations
        Returns structured data that guides the entire query flow
        """
        
        try:
            image_base64 = self._image_to_base64(image)
            
            # Ask AI to analyze and provide structured guidance
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""Analyze this screenshot carefully and answer the user's question.

USER'S QUESTION: {query}

Provide your response in this JSON format:
{{
    "description": "What you see on screen (2-3 sentences, conversational)",
    "has_brand_or_product": true/false,
    "brand_name": "Exact brand/product name if visible, or null",
    "has_price": true/false,
    "price_shown": "Price if visible, or null",
    "needs_web_research": true/false,
    "search_query": "Best search query for research (if needs_web_research is true), or null",
    "why_research": "Brief reason why research is needed, or null"
}}

When to set needs_web_research to true:
- User asks about authenticity, reviews, or recommendations
- User asks "should I buy", "is it real", "is it good"
- User asks about brand/product information
- User asks about pricing or deals
- There's a brand/product visible and user has questions about it

For search_query, if research is needed, create the best possible search query like:
- "[Brand Name] official price India authentic"
- "[Product Name] reviews authenticity check"
- "[Brand] vs alternatives comparison"

Respond ONLY with valid JSON, nothing else."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=600,
                temperature=0.3  # Lower for more consistent JSON
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            # Sometimes AI adds markdown code blocks, so clean it
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            try:
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse JSON from AI: {response_text[:200]}")
                # Fallback to simple analysis
                analysis_data = {
                    "description": response_text,
                    "has_brand_or_product": False,
                    "brand_name": None,
                    "has_price": False,
                    "price_shown": None,
                    "needs_web_research": False,
                    "search_query": None,
                    "why_research": None
                }
            
            return {
                "success": True,
                "analysis": analysis_data["description"],
                "structured_data": analysis_data,
                "needs_web_search": analysis_data.get("needs_web_research", False)
            }
            
        except Exception as e:
            print(f"[ERROR] OpenAI Vision failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None,
                "structured_data": None,
                "needs_web_search": False
            }
    
    async def analyze_screen_only(self, image: Image.Image) -> Dict[str, Any]:
        """Simple screen analysis without query"""
        
        try:
            image_base64 = self._image_to_base64(image)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Briefly describe what's visible on this screen in 1-2 sentences."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return {
                "success": True,
                "description": response.choices[0].message.content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": None
            }


# Singleton instance
openai_vision_service = OpenAIVisionService()