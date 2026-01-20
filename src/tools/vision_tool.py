"""Vision tool for analyzing images using multimodal LLMs."""
import base64
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from src.config import Config
from src.tools.base import Tool

if TYPE_CHECKING:
    from src.execution.docker_context import DockerExecutionContext
    from src.session.conversation_context import ConversationContext


class VisionTool(Tool):
    """Analyze images using a vision-capable LLM."""

    # Supported image formats
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    
    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize vision tool."""
        super().__init__(execution_context, conversation_context)
        self.vision_model = Config.OLLAMA_VISION_MODEL
        self.base_url = Config.OLLAMA_BASE_URL

    @property
    def name(self) -> str:
        return "analyze_image"

    @property
    def description(self) -> str:
        return (
            "Analyze an image using AI vision. Can describe images, read text in images, "
            "identify objects, analyze charts/graphs, and answer questions about images. "
            "Supports: PNG, JPG, JPEG, GIF, WEBP, BMP formats."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file to analyze (relative to workspace)",
                },
                "question": {
                    "type": "string",
                    "description": "Question or instruction about the image (default: 'Describe this image in detail')",
                    "default": "Describe this image in detail",
                },
            },
            "required": ["image_path"],
        }

    def _get_image_path(self, image_path: str) -> Path:
        """Resolve image path relative to workspace."""
        if self.execution_context:
            return self.execution_context.resolve_path(image_path)
        return Path(image_path)

    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, image_path: Path) -> str:
        """Get MIME type for image."""
        ext = image_path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        return mime_types.get(ext, 'image/png')

    async def _analyze_with_ollama(
        self,
        image_base64: str,
        question: str,
        mime_type: str,
    ) -> str:
        """Analyze image using Ollama vision model."""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.vision_model,
            "prompt": question,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.3,
            }
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                return f"Error: Vision API returned status {response.status_code}: {response.text}"
                
            data = response.json()
            return data.get("response", "No response from vision model")

    async def _analyze_with_openrouter(
        self,
        image_base64: str,
        question: str,
        mime_type: str,
    ) -> str:
        """Analyze image using OpenRouter vision model (if available)."""
        # OpenRouter vision models that support images
        vision_models = [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4-vision-preview",
            "google/gemini-pro-vision",
        ]
        
        url = f"{Config.OPENROUTER_BASE_URL}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": vision_models[0],  # Default to Claude
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                return f"Error: OpenRouter Vision API returned status {response.status_code}"
                
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "No response")

    async def execute(
        self,
        image_path: str,
        question: str = "Describe this image in detail",
    ) -> str:
        """Analyze an image.

        Args:
            image_path: Path to the image file.
            question: Question or instruction about the image.

        Returns:
            Analysis result from the vision model.
        """
        try:
            # Resolve and validate path
            full_path = self._get_image_path(image_path)
            
            if not full_path.exists():
                return f"Error: Image not found at {image_path}"
                
            # Check format
            if full_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                return f"Error: Unsupported format {full_path.suffix}. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
                
            # Check file size (limit to 10MB)
            file_size = full_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                return f"Error: Image too large ({file_size / 1024 / 1024:.1f}MB). Maximum: 10MB"
                
            # Encode image
            image_base64 = self._encode_image(full_path)
            mime_type = self._get_mime_type(full_path)
            
            # Try Ollama first (if vision model is available)
            try:
                result = await self._analyze_with_ollama(image_base64, question, mime_type)
                if not result.startswith("Error"):
                    return f"Image Analysis ({full_path.name}):\n\n{result}"
            except Exception as e:
                print(f"[Vision] Ollama failed: {e}")
                
            # Fallback to OpenRouter if API key is available
            if Config.OPENROUTER_API_KEY:
                try:
                    result = await self._analyze_with_openrouter(image_base64, question, mime_type)
                    if not result.startswith("Error"):
                        return f"Image Analysis ({full_path.name}):\n\n{result}"
                except Exception as e:
                    print(f"[Vision] OpenRouter failed: {e}")
                    
            return "Error: Vision analysis failed. No vision model available."
            
        except Exception as e:
            return f"Error analyzing image: {e}"


class ScreenshotTool(Tool):
    """Capture and analyze screenshots (within Docker workspace)."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize screenshot tool."""
        super().__init__(execution_context, conversation_context)
        self.vision_tool = VisionTool(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "analyze_screenshot"

    @property
    def description(self) -> str:
        return (
            "Analyze an existing screenshot or image file. "
            "Useful for verifying visual output of generated content like PDFs, charts, etc."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the screenshot/image file",
                },
                "focus": {
                    "type": "string",
                    "description": "What to focus on (e.g., 'text content', 'layout', 'colors', 'errors')",
                    "default": "overall content and layout",
                },
            },
            "required": ["image_path"],
        }

    async def execute(
        self,
        image_path: str,
        focus: str = "overall content and layout",
    ) -> str:
        """Analyze a screenshot.

        Args:
            image_path: Path to the screenshot.
            focus: What aspect to focus on.

        Returns:
            Analysis result.
        """
        question = f"Analyze this screenshot. Focus on: {focus}. Describe what you see, identify any issues, and note important details."
        return await self.vision_tool.execute(image_path, question)


class ChartAnalyzerTool(Tool):
    """Specialized tool for analyzing charts and graphs."""

    def __init__(
        self,
        execution_context: Optional["DockerExecutionContext"] = None,
        conversation_context: Optional["ConversationContext"] = None,
    ) -> None:
        """Initialize chart analyzer."""
        super().__init__(execution_context, conversation_context)
        self.vision_tool = VisionTool(execution_context, conversation_context)

    @property
    def name(self) -> str:
        return "analyze_chart"

    @property
    def description(self) -> str:
        return (
            "Analyze a chart, graph, or data visualization. "
            "Can extract data points, identify trends, and describe the visualization."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the chart/graph image",
                },
                "chart_type": {
                    "type": "string",
                    "description": "Type of chart (e.g., 'bar', 'line', 'pie', 'scatter', 'auto')",
                    "default": "auto",
                },
            },
            "required": ["image_path"],
        }

    async def execute(
        self,
        image_path: str,
        chart_type: str = "auto",
    ) -> str:
        """Analyze a chart or graph.

        Args:
            image_path: Path to the chart image.
            chart_type: Type of chart (or 'auto' for detection).

        Returns:
            Analysis of the chart.
        """
        question = f"""Analyze this chart/graph. Please provide:
1. Chart type (bar, line, pie, etc.)
2. Title and labels (if visible)
3. Key data points or values
4. Main trends or insights
5. Any notable observations

{"Hint: This appears to be a " + chart_type + " chart." if chart_type != "auto" else ""}"""

        return await self.vision_tool.execute(image_path, question)
