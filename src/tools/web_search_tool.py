"""Web search tool with multiple fallback sources."""
import urllib.parse
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class WebSearchTool(Tool):
    """Search the web using multiple sources with fallbacks."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize web search tool."""
        super().__init__(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web using multiple sources (DuckDuckGo, Wikipedia, GitHub). "
            "Returns search results with titles, URLs, and snippets. "
            "Automatically falls back to alternative sources if one fails."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'Python web frameworks comparison')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5, max: 10)",
                    "default": 5,
                },
                "source": {
                    "type": "string",
                    "description": "Preferred source: 'auto' (default), 'duckduckgo', 'wikipedia', 'github'",
                    "default": "auto",
                },
            },
            "required": ["query"],
        }

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    snippet = r.get("body", "")[:150]
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": snippet,
                        "source": "DuckDuckGo",
                    })
            return results
        except Exception as e:
            print(f"[WebSearch] DuckDuckGo failed: {e}")
            return []

    async def _search_wikipedia(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using Wikipedia API (free, no key required)."""
        try:
            import httpx
            
            # Wikipedia API search endpoint
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json",
                "utf8": 1,
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                data = response.json()
                
            results: List[Dict[str, str]] = []
            for item in data.get("query", {}).get("search", []):
                # Clean snippet (remove HTML)
                import re
                snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))[:150]
                
                results.append({
                    "title": item.get("title", ""),
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(item.get('title', '').replace(' ', '_'))}",
                    "snippet": snippet,
                    "source": "Wikipedia",
                })
            return results
        except Exception as e:
            print(f"[WebSearch] Wikipedia failed: {e}")
            return []

    async def _search_github(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search GitHub repositories (free, no key required for basic search)."""
        try:
            import httpx
            
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "per_page": max_results,
                "sort": "stars",
                "order": "desc",
            }
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Agent-Search",
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)
                data = response.json()
                
            results: List[Dict[str, str]] = []
            for item in data.get("items", []):
                snippet = item.get("description", "")
                if snippet:
                    snippet = snippet[:150]
                else:
                    snippet = f"Stars: {item.get('stargazers_count', 0)}, Language: {item.get('language', 'N/A')}"
                    
                results.append({
                    "title": f"{item.get('full_name', '')} - {item.get('language', 'N/A')}",
                    "url": item.get("html_url", ""),
                    "snippet": snippet,
                    "source": "GitHub",
                })
            return results
        except Exception as e:
            print(f"[WebSearch] GitHub failed: {e}")
            return []

    async def _search_arxiv(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search arXiv for scientific papers (free, no key required)."""
        try:
            import httpx
            
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params)
                
            # Parse XML response
            import re
            results: List[Dict[str, str]] = []
            
            entries = re.findall(r'<entry>(.*?)</entry>', response.text, re.DOTALL)
            for entry in entries[:max_results]:
                title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                id_match = re.search(r'<id>(.*?)</id>', entry)
                
                title = title_match.group(1).strip() if title_match else "Untitled"
                summary = summary_match.group(1).strip()[:150] if summary_match else ""
                url = id_match.group(1) if id_match else ""
                
                results.append({
                    "title": title.replace('\n', ' '),
                    "url": url,
                    "snippet": summary.replace('\n', ' '),
                    "source": "arXiv",
                })
            return results
        except Exception as e:
            print(f"[WebSearch] arXiv failed: {e}")
            return []

    async def execute(self, query: str, max_results: int = 5, source: str = "auto") -> str:
        """Execute web search with fallbacks.

        Args:
            query: Search query.
            max_results: Maximum number of results (default: 5).
            source: Preferred source or 'auto' for fallback.

        Returns:
            Formatted search results.
        """
        max_results = min(max_results, 10)
        results: List[Dict[str, str]] = []
        sources_tried: List[str] = []

        # Define search order based on query type
        if source == "auto":
            # Detect query type and prioritize sources
            query_lower = query.lower()
            
            if any(kw in query_lower for kw in ["github", "repo", "code", "library", "package"]):
                search_order = [
                    ("GitHub", self._search_github),
                    ("DuckDuckGo", self._search_duckduckgo),
                ]
            elif any(kw in query_lower for kw in ["paper", "research", "study", "arxiv", "scientific"]):
                search_order = [
                    ("arXiv", self._search_arxiv),
                    ("Wikipedia", self._search_wikipedia),
                    ("DuckDuckGo", self._search_duckduckgo),
                ]
            elif any(kw in query_lower for kw in ["what is", "define", "meaning", "history", "wiki"]):
                search_order = [
                    ("Wikipedia", self._search_wikipedia),
                    ("DuckDuckGo", self._search_duckduckgo),
                ]
            else:
                # Default order
                search_order = [
                    ("DuckDuckGo", self._search_duckduckgo),
                    ("Wikipedia", self._search_wikipedia),
                    ("GitHub", self._search_github),
                ]
        else:
            # Use specific source
            source_map = {
                "duckduckgo": ("DuckDuckGo", self._search_duckduckgo),
                "wikipedia": ("Wikipedia", self._search_wikipedia),
                "github": ("GitHub", self._search_github),
                "arxiv": ("arXiv", self._search_arxiv),
            }
            if source.lower() in source_map:
                search_order = [source_map[source.lower()]]
            else:
                search_order = [("DuckDuckGo", self._search_duckduckgo)]

        # Try each source until we get results
        for source_name, search_fn in search_order:
            sources_tried.append(source_name)
            results = await search_fn(query, max_results)
            if results:
                break

        if not results:
            return f"No results found for: {query}\nSources tried: {', '.join(sources_tried)}"

        # Format results
        output_lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            output_lines.append(f"{i}. [{r['source']}] {r['title']}")
            output_lines.append(f"   URL: {r['url']}")
            output_lines.append(f"   {r['snippet']}")
            output_lines.append("")

        return "\n".join(output_lines)


class WebNewsSearchTool(Tool):
    """Search for news using DuckDuckGo."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize news search tool."""
        super().__init__(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "news_search"

    @property
    def description(self) -> str:
        return (
            "Search for recent news articles using DuckDuckGo News. "
            "Returns news articles with titles, URLs, dates, and snippets. "
            "Use this for current events and recent news."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "News search query (e.g., 'AI developments 2025')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5, max: 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5) -> str:
        """Execute news search.

        Args:
            query: News search query.
            max_results: Maximum number of results (default: 5).

        Returns:
            Formatted news results.
        """
        try:
            from duckduckgo_search import DDGS

            max_results = min(max_results, 10)

            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    snippet = r.get("body", "")[:120]
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "date": r.get("date", ""),
                        "source": r.get("source", ""),
                        "snippet": snippet,
                    })

            if not results:
                return f"No news found for: {query}"

            output_lines = [f"News results for: {query}\n"]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['title']}")
                output_lines.append(f"   URL: {r['url']}")
                output_lines.append(f"   Date: {r['date']} | Source: {r['source']}")
                output_lines.append(f"   {r['snippet']}")
                output_lines.append("")

            return "\n".join(output_lines)

        except ImportError:
            return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
        except Exception as exc:
            return f"Error searching news: {exc}"
