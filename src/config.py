import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM settings (Ollama)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://100.68.221.26:11434")
    
    # Model selection - different models for different tasks
    OLLAMA_MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "mistral:latest")  # Fast for simple tasks
    OLLAMA_MODEL_CODE = os.getenv("OLLAMA_MODEL_CODE", "qwen3-coder:30b")  # Specialized for code generation
    OLLAMA_MODEL_GENERAL = os.getenv("OLLAMA_MODEL_GENERAL", "qwen3:32b")  # General reasoning
    
    # Default model - using GENERAL for better reasoning (slower but more reliable)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL_GENERAL)
    
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "20"))

    # Docker workspace settings
    WORKSPACE_BASE_DIR = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    SESSIONS_DIR = WORKSPACE_BASE_DIR / "sessions"
    DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
    WORKSPACE_MOUNT_PATH = "/workspace"
    AUTO_CLEANUP = os.getenv("AUTO_CLEANUP", "false").lower() == "true"

    # Session settings
    CONTEXT_AUTOSAVE = os.getenv("CONTEXT_AUTOSAVE", "true").lower() == "true"
