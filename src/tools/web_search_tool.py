"""Web search tool using DuckDuckGo."""
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class WebSearchTool(Tool):
    """Search the web using DuckDuckGo."""

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
            "Search the web using DuckDuckGo. "
            "Returns search results with titles, URLs, and snippets. "
            "Use this to find information, research topics, or get current data."
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
            },
            "required": ["query"],
        }

    async def execute(self, query: str, max_results: int = 5) -> str:
        """Execute web search.

        Args:
            query: Search query.
            max_results: Maximum number of results (default: 5).

        Returns:
            Formatted search results.
        """
        try:
            from duckduckgo_search import DDGS

            # Limit max_results to prevent abuse
            max_results = min(max_results, 10)

            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            if not results:
                return f"No results found for: {query}"

            # Format results
            output_lines = [f"Search results for: {query}\n"]
            for i, r in enumerate(results, 1):
                output_lines.append(f"{i}. {r['title']}")
                output_lines.append(f"   URL: {r['url']}")
                output_lines.append(f"   {r['snippet']}")
                output_lines.append("")

            return "\n".join(output_lines)

        except ImportError:
            return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
        except Exception as exc:
            return f"Error searching web: {exc}"


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
            max_results: Maximum number of results.

        Returns:
            Formatted news results.
        """
        try:
            from duckduckgo_search import DDGS

            max_results = min(max_results, 10)

            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.news(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "date": r.get("date", ""),
                        "source": r.get("source", ""),
                        "snippet": r.get("body", ""),
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
