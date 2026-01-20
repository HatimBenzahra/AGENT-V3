"""FastAPI application for the ReAct Agent."""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat, files, sessions
from src.api.websocket.handler import active_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Starting ReAct Agent API...")
    yield
    # Cleanup: close all active connections
    print("Shutting down ReAct Agent API...")
    for session_id, conn in list(active_connections.items()):
        try:
            await conn["websocket"].close()
        except Exception:
            pass


app = FastAPI(
    title="ReAct Agent API",
    description="API for the ReAct Agent with real-time WebSocket support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(files.router, prefix="/api/files", tags=["files"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ReAct Agent API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
