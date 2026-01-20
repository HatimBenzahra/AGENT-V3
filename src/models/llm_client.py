"""LLM client supporting OpenRouter and Ollama."""
from typing import Dict, List, Optional

import httpx

from src.config import Config


class LLMClient:
    """LLM client supporting multiple providers (OpenRouter, Ollama)."""
    
    def __init__(self) -> None:
        """Initialize LLM client based on configuration."""
        self.provider = Config.LLM_PROVIDER.lower()
        
        if self.provider == "openrouter":
            self.api_key = Config.OPENROUTER_API_KEY
            self.base_url = Config.OPENROUTER_BASE_URL
            self.model = Config.OPENROUTER_MODEL
            
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY not set in .env")
                
            print(f"[LLM] Using OpenRouter with model: {self.model}")
        else:
            # Fallback to Ollama
            self.base_url = Config.OLLAMA_BASE_URL
            self.model = Config.OLLAMA_MODEL
            self.api_key = None
            print(f"[LLM] Using Ollama at {self.base_url} with model: {self.model}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = 4096,
    ) -> str:
        """Send chat completion request.
        
        Args:
            messages: Conversation messages.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            
        Returns:
            The model's response content.
        """
        if self.provider == "openrouter":
            return await self._openrouter_completion(messages, temperature, max_tokens)
        else:
            return await self._ollama_completion(messages, temperature, max_tokens)

    async def _openrouter_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Send request to OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # Required by OpenRouter
            "X-Title": "ReAct Agent",  # Optional, shows in OpenRouter dashboard
        }
        
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_body,
            )
            
            if response.status_code != 200:
                error_text = response.text
                raise Exception(f"OpenRouter API error ({response.status_code}): {error_text}")
            
            data = response.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                raise Exception(f"Invalid response from OpenRouter: {data}")
            
            return data["choices"][0]["message"]["content"]

    async def _ollama_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Send request to Ollama API."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            request_body = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            }
            if max_tokens:
                request_body["options"]["num_predict"] = max_tokens
            
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
