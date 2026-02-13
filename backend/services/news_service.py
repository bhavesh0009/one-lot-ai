
import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class NewsService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    def fetch_news(self, query: str, type: str = "market"):
        """
        Fetch news using Google Gemini Grounded Search (Official API).
        Uses model: gemini-2.5-flash
        
        Args:
            query (str): The search query or ticker symbol.
            type (str): 'market' or 'stock'.
            
        Returns:
            dict: Structured response with text and citations.
        """
        if not self.client:
            return {
                "error": "Gemini API key not configured.",
                "text": "News service unavailable.",
                "sources": []
            }

        try:
            # Construct prompt
            if type == "stock":
                prompt = f"What are the latest intraday news and major announcements for {query} stock in India today? Summarize key triggers and sentiment in markdown bullet points. Keep it concise."
            else:
                prompt = "What are the latest key news headlines and market sentiment for the Indian stock market today? Focus on Nifty/Sensex and major sectors. Summarize in markdown bullet points."

            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["TEXT"],
                temperature=0.3
            )

            # Use gemini-2.5-flash as verified
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config=config
            )

            return self._process_response(response)

        except Exception as e:
            logger.error(f"Error fetching news from Gemini: {e}")
            return {
                "error": str(e),
                "text": "Failed to fetch news.",
                "sources": []
            }

    def _process_response(self, response):
        """Extract text and sources from Gemini response."""
        result = {
            "text": "",
            "sources": [],
            "search_queries": []
        }

        if not response or not response.candidates:
            return result
        
        candidate = response.candidates[0]
        
        # Get text content
        if candidate.content and candidate.content.parts:
            result["text"] = "".join([part.text for part in candidate.content.parts if part.text])

        # Get grounding metadata
        if candidate.grounding_metadata:
            meta = candidate.grounding_metadata
            
            # Grounding chunks (sources)
            if meta.grounding_chunks:
                for chunk in meta.grounding_chunks:
                    if chunk.web:
                        result["sources"].append({
                            "title": chunk.web.title,
                            "url": chunk.web.uri
                        })
            
            # Search queries used
            if meta.web_search_queries:
                result["search_queries"] = meta.web_search_queries

        return result

# Singleton instance
news_service = NewsService()
