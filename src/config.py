import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM settings
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "20"))

    # Docker workspace settings
    WORKSPACE_BASE_DIR = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
    SESSIONS_DIR = WORKSPACE_BASE_DIR / "sessions"
    DOCKER_IMAGE = os.getenv("DOCKER_IMAGE", "python:3.11-slim")
    WORKSPACE_MOUNT_PATH = "/workspace"
    AUTO_CLEANUP = os.getenv("AUTO_CLEANUP", "false").lower() == "true"

    # Session settings
    CONTEXT_AUTOSAVE = os.getenv("CONTEXT_AUTOSAVE", "true").lower() == "true"
