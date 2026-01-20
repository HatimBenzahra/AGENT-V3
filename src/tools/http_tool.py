"""HTTP client tool for fetching URLs."""
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class HttpClientTool(Tool):
    """Make HTTP requests to fetch content from URLs."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize HTTP client tool."""
        super().__init__(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "http_request"

    @property
    def description(self) -> str:
        return (
            "Make HTTP requests to fetch content from URLs. "
            "Supports GET and POST methods. "
            "Use this to fetch web pages, APIs, or download content."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch (e.g., 'https://example.com/api/data')",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method: GET or POST (default: GET)",
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers as key-value pairs",
                },
                "body": {
                    "type": "string",
                    "description": "Request body for POST requests",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> str:
        """Execute HTTP request.

        Args:
            url: URL to fetch.
            method: HTTP method (GET or POST).
            headers: Optional HTTP headers.
            body: Optional request body for POST.

        Returns:
            Response content or error message.
        """
        try:
            import httpx

            method = method.upper()
            if method not in ("GET", "POST"):
                return f"Error: Unsupported method '{method}'. Use GET or POST."

            # Default headers
            default_headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ReActAgent/1.0)",
            }
            if headers:
                default_headers.update(headers)

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                if method == "GET":
                    response = await client.get(url, headers=default_headers)
                else:  # POST
                    response = await client.post(
                        url,
                        headers=default_headers,
                        content=body,
                    )

                # Build response info
                result_parts = [
                    f"URL: {url}",
                    f"Status: {response.status_code} {response.reason_phrase}",
                    f"Content-Type: {response.headers.get('content-type', 'unknown')}",
                    "",
                ]

                # Get content
                content_type = response.headers.get("content-type", "")
                content = response.text

                # Truncate to save tokens
                max_length = 4000
                if len(content) > max_length:
                    content = content[:max_length] + f"\n\n... [Truncated]"

                result_parts.append("Content:")
                result_parts.append(content)

                return "\n".join(result_parts)

        except httpx.TimeoutException:
            return f"Error: Request timed out for URL: {url}"
        except httpx.RequestError as exc:
            return f"Error making request: {exc}"
        except Exception as exc:
            return f"Error: {exc}"


class FetchWebPageTool(Tool):
    """Fetch and extract text content from a web page."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize fetch web page tool."""
        super().__init__(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "fetch_webpage"

    @property
    def description(self) -> str:
        return (
            "Fetch a web page and extract its text content. "
            "Removes HTML tags and returns readable text. "
            "Use this to read articles, documentation, or web content."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the web page to fetch",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str) -> str:
        """Fetch web page and extract text.

        Args:
            url: URL to fetch.

        Returns:
            Extracted text content.
        """
        try:
            import httpx
            import re

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ReActAgent/1.0)",
            }

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                html = response.text

                # Simple HTML to text conversion
                # Remove script and style elements
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', html)

                # Decode HTML entities
                text = text.replace('&nbsp;', ' ')
                text = text.replace('&amp;', '&')
                text = text.replace('&lt;', '<')
                text = text.replace('&gt;', '>')
                text = text.replace('&quot;', '"')
                text = text.replace('&#39;', "'")

                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text)
                text = text.strip()

                # Truncate to save tokens (4000 chars is enough for most use cases)
                max_length = 4000
                if len(text) > max_length:
                    text = text[:max_length] + f"\n\n... [Truncated, {len(text)} total chars]"

                return f"Content from: {url}\n\n{text}"

        except httpx.HTTPStatusError as exc:
            return f"Error: HTTP {exc.response.status_code} for URL: {url}"
        except httpx.TimeoutException:
            return f"Error: Request timed out for URL: {url}"
        except Exception as exc:
            return f"Error fetching page: {exc}"
