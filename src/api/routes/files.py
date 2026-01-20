"""File access endpoints."""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel

from src.config import Config
from src.session.session_manager import SessionManager

router = APIRouter()
session_manager = SessionManager()


class FileInfo(BaseModel):
    """File information."""
    name: str
    path: str
    size: int
    is_directory: bool


class FileListResponse(BaseModel):
    """List of files response."""
    files: List[FileInfo]
    directory: str


class FileContentResponse(BaseModel):
    """File content response."""
    path: str
    content: str
    size: int


@router.get("/{session_id}/list")
async def list_files(session_id: str, path: str = "") -> FileListResponse:
    """List files in a session workspace."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Config.SESSIONS_DIR / session_id / "files"
    if not workspace.exists():
        return FileListResponse(files=[], directory=path)

    target_dir = workspace / path if path else workspace

    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    # Security check: ensure path is within workspace
    try:
        target_dir.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    files = []
    for item in sorted(target_dir.iterdir()):
        if item.name.startswith("."):
            continue
        files.append(FileInfo(
            name=item.name,
            path=str(item.relative_to(workspace)),
            size=item.stat().st_size if item.is_file() else 0,
            is_directory=item.is_dir(),
        ))

    return FileListResponse(files=files, directory=path)


@router.get("/{session_id}/read")
async def read_file(session_id: str, path: str) -> FileContentResponse:
    """Read a file from session workspace."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Config.SESSIONS_DIR / session_id / "files"
    file_path = workspace / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Security check
    try:
        file_path.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        content = file_path.read_text(encoding="utf-8")
        return FileContentResponse(
            path=path,
            content=content,
            size=len(content),
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not text readable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/download")
async def download_file(session_id: str, path: str):
    """Download a file from session workspace."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    workspace = Config.SESSIONS_DIR / session_id / "files"
    file_path = workspace / path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Security check
    try:
        file_path.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/{session_id}/outputs")
async def list_outputs(session_id: str) -> List[dict]:
    """List outputs for a session."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    outputs_dir = Config.SESSIONS_DIR / session_id / "outputs"
    if not outputs_dir.exists():
        return []

    outputs = []
    for output_file in sorted(outputs_dir.glob("*.json")):
        try:
            import json
            data = json.loads(output_file.read_text())
            outputs.append({
                "filename": output_file.name,
                "task": data.get("task", ""),
                "timestamp": data.get("timestamp", ""),
            })
        except Exception:
            continue

    return outputs


@router.get("/{session_id}/outputs/{filename}")
async def get_output(session_id: str, filename: str) -> dict:
    """Get a specific output."""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    output_file = Config.SESSIONS_DIR / session_id / "outputs" / filename
    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    try:
        import json
        return json.loads(output_file.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
