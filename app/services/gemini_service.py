"""
Gemini AI Service for vision and text processing
"""
import google.generativeai as genai
from PIL import Image
import io
from typing import Optional, Dict, Any
from app.config import settings


class GeminiService:
    """Service for interacting with Google Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini AI client"""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Try without the models/ prefix for the GenerativeModel
        model_name = settings.GEMINI_MODEL.replace('models/', '')
        self.model = genai.GenerativeModel(model_name)
        
    async def analyze_screen_with_query(
        self, 
        image: Image.Image, 
        query: str
    ) -> Dict[str, Any]:
        """
        Analyze a screenshot with user's query
        
        Args:
            image: PIL Image of the screen
            query: User's question/query
            
        Returns:
            Dict with analysis results
        """
        prompt = f"""You are Saathi, an intelligent AI companion helping users understand what they're seeing on their phone screen.

USER'S SCREEN: Analyze this screenshot carefully.
USER'S QUESTION: {query}

Your task:
1. Identify what app/platform this is from
2. Understand the main content visible (ads, posts, products, articles, etc.)
3. If there are any brands, products, or services mentioned, identify them
4. Answer the user's question based on what you see

Provide a helpful, conversational response. If you see a brand or product, mention:
- What it is
- Key details visible on screen
- Whether the user should search for more info

Keep your response concise (2-3 sentences) unless the user asks for detailed analysis.
"""
        
        try:
            response = self.model.generate_content([prompt, image])
            return {
                "success": True,
                "analysis": response.text,
                "needs_web_search": self._needs_web_search(response.text, query)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis": None,
                "needs_web_search": False
            }
    
    async def generate_response(
        self, 
        query: str, 
        context: Optional[str] = None,
        search_results: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent response based on query and context
        
        Args:
            query: User's question
            context: Optional screen analysis context
            search_results: Optional web search results
            
        Returns:
            Dict with response
        """
        prompt = f"""You are Saathi, a helpful AI companion speaking to a user in India.

USER'S QUESTION: {query}

{f"SCREEN CONTEXT: {context}" if context else ""}

{f"WEB SEARCH RESULTS: {search_results}" if search_results else ""}

Provide a helpful, conversational response. Be:
- Friendly and warm (you're a companion, not just an assistant)
- Concise but informative
- Honest if you don't know something
- Use mix of Hindi and English naturally if appropriate

If discussing brands/products, mention:
- Key information about quality, pricing, reviews
- Any red flags or things to watch out for
- Whether it's a good choice

Keep response to 3-4 sentences unless user asks for detailed analysis.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return {
                "success": True,
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "Sorry, I encountered an error processing your request."
            }
    
    async def analyze_screen_only(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze screenshot without specific query
        Used when user just wants to know what's on screen
        """
        prompt = """Briefly describe what's visible on this screen:
- What app is this?
- What's the main content?
- Any notable brands, products, or information?

Keep it very brief (1-2 sentences)."""
        
        try:
            response = self.model.generate_content([prompt, image])
            return {
                "success": True,
                "description": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": None
            }
    
    def _needs_web_search(self, analysis: str, query: str) -> bool:
        """
        Determine if web search would be helpful
        Simple heuristic: look for brand names, products, or requests for reviews
        """
        search_indicators = [
            "brand", "product", "company", "review", "price", 
            "authentic", "trust", "worth it", "good", "bad",
            "should i buy", "is this", "tell me more"
        ]
        
        query_lower = query.lower()
        analysis_lower = analysis.lower()
        
        return any(indicator in query_lower or indicator in analysis_lower 
                  for indicator in search_indicators)


# Singleton instance
gemini_service = GeminiService()
