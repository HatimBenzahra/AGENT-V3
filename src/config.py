import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM Provider: "openrouter" or "ollama"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
    
    # OpenRouter settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324")
    
    # Ollama settings (fallback)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://100.68.221.26:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:32b")
    OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:32b")
    
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "100"))  # High for long documents

    # Docker workspace settings
    WORKSPACE_BASE_DIR = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    SESSIONS_DIR = WORKSPACE_BASE_DIR / "sessions"
    DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
    WORKSPACE_MOUNT_PATH = "/workspace"
    AUTO_CLEANUP = os.getenv("AUTO_CLEANUP", "false").lower() == "true"

    # Session settings
    CONTEXT_AUTOSAVE = os.getenv("CONTEXT_AUTOSAVE", "true").lower() == "true"
