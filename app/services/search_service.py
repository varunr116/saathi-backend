"""
Google Custom Search Service for web research
"""
import requests
from typing import Dict, Any, List, Optional
from app.config import settings


class SearchService:
    """Service for web search using Google Custom Search API"""
    
    def __init__(self):
        """Initialize search service"""
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    async def search(
        self, 
        query: str, 
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform web search
        
        Args:
            query: Search query
            num_results: Number of results to return (1-10)
            
        Returns:
            Dict with search results
        """
        if not self.api_key or not self.engine_id:
            return {
                "success": False,
                "error": "Search API not configured",
                "results": []
            }
        
        try:
            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": min(num_results, 10)
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            results = []
            if "items" in data:
                for item in data["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("displayLink", "")
                    })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results)
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Search request failed: {str(e)}",
                "results": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def search_brand(self, brand_name: str) -> Dict[str, Any]:
        """
        Search for brand information, reviews, and authenticity
        
        Args:
            brand_name: Name of the brand to search
            
        Returns:
            Dict with brand information
        """
        # Create focused queries for brand research
        queries = [
            f"{brand_name} reviews",
            f"{brand_name} authentic or fake",
            f"{brand_name} pricing India"
        ]
        
        all_results = []
        for query in queries:
            result = await self.search(query, num_results=3)
            if result["success"]:
                all_results.extend(result["results"])
        
        return {
            "success": True,
            "brand": brand_name,
            "results": all_results[:8],  # Top 8 most relevant
            "summary": self._create_summary(all_results[:8])
        }
    
    def _create_summary(self, results: List[Dict]) -> str:
        """Create a text summary from search results"""
        if not results:
            return "No search results found."
        
        summary_parts = []
        for i, result in enumerate(results[:5], 1):
            summary_parts.append(
                f"{i}. {result['title']} - {result['snippet']}"
            )
        
        return "\n".join(summary_parts)


# Singleton instance
search_service = SearchService()
