"""
Groq LLM Service for text processing - Pure English responses
"""
from groq import Groq
from typing import Optional, Dict, Any
from app.config import settings


class GroqLLMService:
    """Service for using Groq's LLM capabilities"""
    
    def __init__(self):
        """Initialize Groq client"""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.text_model = "llama-3.3-70b-versatile"
        
    async def generate_response(
        self, 
        query: str, 
        context: Optional[str] = None,
        search_results: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate intelligent response in pure English"""
        
        prompt = f"""You are Saathi, a helpful AI companion for users in India.

USER'S QUESTION: {query}

{f"SCREEN CONTEXT: {context}" if context else ""}

{f"WEB SEARCH RESULTS (use this information to answer directly):\n{search_results}" if search_results else ""}

IMPORTANT INSTRUCTIONS:
- Respond in PURE ENGLISH ONLY - no Hindi words or Hinglish
- If you have web search results, USE THEM to answer the user's question directly
- DON'T tell the user to "check the website" or "search online" - YOU do the research and tell them
- Provide specific information: prices, reviews, authenticity checks, official sources
- Be helpful and proactive, not lazy
- If asking about brand authenticity, tell them if it's likely real or fake based on the search results
- Cite official prices and compare with what user is seeing
- Make concrete recommendations based on the information

Provide a helpful, conversational response. Be:
- Friendly and warm (you're a companion, not just an assistant)
- Professional and clear
- Concise but informative (2-4 sentences unless asked for detail)
- Direct and actionable - give clear recommendations
- ALWAYS in pure English only

Keep response short unless user asks for detailed analysis."""
        
        try:
            completion = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Saathi, a helpful English-speaking AI companion who does research for users. Always respond in pure English only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500,
                top_p=1,
                stream=False
            )
            
            return {
                "success": True,
                "response": completion.choices[0].message.content
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "Sorry, I encountered an error processing your request."
            }


# Singleton instance
groq_llm_service = GroqLLMService()