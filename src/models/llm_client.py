"""LLM client with intelligent model selection."""
import re
from enum import Enum
from typing import Dict, List, Optional

import httpx

from src.config import Config


class ModelType(Enum):
    """Available model types for different tasks."""
    FAST = "fast"       # Quick responses, simple tasks
    CODE = "code"       # Code generation and programming
    GENERAL = "general" # Complex reasoning


class LLMClient:
    """LLM client for Ollama API with intelligent model selection."""
    
    # Keywords that indicate code-related tasks
    CODE_KEYWORDS = [
        "code", "script", "program", "function", "class", "implement",
        "create a python", "create a javascript", "create a typescript",
        "write a python", "write a javascript", "write code",
        "build", "develop", "algorithm", "api", "database",
        "html", "css", "react", "vue", "django", "flask", "fastapi",
        "debug", "fix the code", "refactor", "optimize code",
    ]
    
    # Keywords that indicate need for complex reasoning
    COMPLEX_KEYWORDS = [
        "analyze", "explain in detail", "compare", "evaluate",
        "design", "architecture", "plan", "strategy",
    ]
    
    def __init__(self, model_type: Optional[ModelType] = None) -> None:
        """Initialize LLM client.
        
        Args:
            model_type: Optional specific model type. If None, auto-selects based on task.
        """
        self.base_url = Config.OLLAMA_BASE_URL
        self.default_model_type = model_type
        
        # Model mapping
        self.models = {
            ModelType.FAST: Config.OLLAMA_MODEL_FAST,
            ModelType.CODE: Config.OLLAMA_MODEL_CODE,
            ModelType.GENERAL: Config.OLLAMA_MODEL_GENERAL,
        }
        
        self.current_model = self._get_model(model_type or ModelType.FAST)
        print(f"[LLM] Initialized with Ollama at {self.base_url}")
        print(f"[LLM] Available models: FAST={Config.OLLAMA_MODEL_FAST}, CODE={Config.OLLAMA_MODEL_CODE}, GENERAL={Config.OLLAMA_MODEL_GENERAL}")

    def _get_model(self, model_type: ModelType) -> str:
        """Get model name for given type."""
        return self.models.get(model_type, Config.OLLAMA_MODEL_FAST)

    def _detect_task_type(self, messages: List[Dict[str, str]]) -> ModelType:
        """Detect the best model type based on message content.
        
        Args:
            messages: The conversation messages.
            
        Returns:
            The recommended ModelType for this task.
        """
        # Get the user's task from messages
        task_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                task_content += " " + msg.get("content", "")
        
        task_lower = task_content.lower()
        
        # Check for code-related keywords
        for keyword in self.CODE_KEYWORDS:
            if keyword in task_lower:
                return ModelType.CODE
        
        # Check for complex reasoning keywords
        for keyword in self.COMPLEX_KEYWORDS:
            if keyword in task_lower:
                return ModelType.GENERAL
        
        # Default to GENERAL model for better reasoning (mistral too weak for ReAct)
        return ModelType.GENERAL

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        model_type: Optional[ModelType] = None,
        auto_select: bool = True,
    ) -> str:
        """Send chat completion request to Ollama.
        
        Args:
            messages: Conversation messages.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            model_type: Force specific model type.
            auto_select: If True and model_type is None, auto-select based on task.
            
        Returns:
            The model's response content.
        """
        # Determine which model to use
        if model_type:
            selected_model = self._get_model(model_type)
        elif self.default_model_type:
            selected_model = self._get_model(self.default_model_type)
        elif auto_select:
            detected_type = self._detect_task_type(messages)
            selected_model = self._get_model(detected_type)
            print(f"[LLM] Auto-selected model: {selected_model} (type: {detected_type.value})")
        else:
            selected_model = self._get_model(ModelType.FAST)
        
        self.current_model = selected_model
        print(f"[LLM] Using model: {selected_model}")
        
        # Set appropriate timeout based on model size
        timeout = 120.0 if "mistral" in selected_model else 600.0  # 2min for fast, 10min for large
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            request_body = {
                "model": selected_model,
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

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        temperature: float = 0.1,
    ) -> str:
        """Generate code using the code-specialized model.
        
        Args:
            prompt: Description of what code to generate.
            language: Target programming language.
            temperature: Lower = more deterministic.
            
        Returns:
            Generated code.
        """
        messages = [
            {
                "role": "system",
                "content": f"You are an expert {language} programmer. Generate clean, well-documented, production-quality code. Only output the code, no explanations unless asked."
            },
            {"role": "user", "content": prompt}
        ]
        
        return await self.chat_completion(
            messages,
            temperature=temperature,
            model_type=ModelType.CODE,
        )
