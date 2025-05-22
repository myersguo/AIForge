from tavily import TavilyClient

from app.config.settings import settings


class SearchEngine:
    def __init__(self):
        self.client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    def search(self, query: str, max_results: int = 10):
        """
        Execute a search query using Tavily.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        try:
            print(f"Executing search with query: {query}")
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=False,
                include_raw_content=False,
                include_images=True,
            )
            print(f"Search response: {response}")
            return response
        except Exception as e:
            raise ValueError(f"Search failed: {str(e)}") from e
