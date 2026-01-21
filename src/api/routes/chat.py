"""Chat WebSocket endpoint."""
import json
import traceback
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.websocket.handler import (
    active_connections,
    create_session_with_tools,
    handle_websocket_message,
    send_message,
)
from src.session.conversation_context import ConversationContext

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: Optional[str] = None,
):
    """WebSocket endpoint for real-time chat with the agent."""
    await websocket.accept()
    print(f"[WS] Connection accepted, session_id={session_id}")
    
    actual_session_id = session_id
    session_initialized = False
    state = {
        "session": None,
        "registry": None,
        "is_processing": False,
        "should_interrupt": False,
    }

    try:
        # Send initial connected message without creating session yet
        await send_message(
            websocket, "connected",
            session_id=session_id or "new",
            workspace="",
        )
        print(f"[WS] Sent connected message")

        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                print(f"[WS] Received: {data[:100]}...")
                message = json.loads(data)
                
                # Lazy initialize session on first chat or request_plan message
                if message.get("type") in ("chat", "request_plan") and not session_initialized:
                    print(f"[WS] Initializing session...")
                    await send_message(websocket, "initializing", message="Starting session...")
                    
                    # Check if resuming existing session
                    if session_id and ConversationContext.exists(session_id):
                        print(f"[WS] Resuming session {session_id}")
                        session, registry = await create_session_with_tools(session_id)
                    else:
                        print(f"[WS] Creating new session")
                        session, registry = await create_session_with_tools(None)
                    
                    actual_session_id = session.session_id
                    state["session"] = session
                    state["registry"] = registry
                    session_initialized = True
                    
                    # Store in active connections
                    active_connections[actual_session_id] = {
                        "websocket": websocket,
                        "state": state,
                    }
                    
                    # Send updated session info
                    await send_message(
                        websocket, "session_ready",
                        session_id=actual_session_id,
                        workspace=str(session.docker_context.workspace_dir),
                    )
                    print(f"[WS] Session ready: {actual_session_id}")
                
                if session_initialized:
                    print(f"[WS] Handling message...")
                    await handle_websocket_message(websocket, message, state)
                elif message.get("type") not in ("chat", "request_plan"):
                    await send_message(websocket, "error", message="Send a chat or project request to start the session")
                    
            except json.JSONDecodeError as e:
                print(f"[WS] JSON decode error: {e}")
                await send_message(websocket, "error", message="Invalid JSON")

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        traceback.print_exc()
        try:
            await send_message(websocket, "error", message=str(e))
        except Exception:
            pass
    finally:
        print(f"[WS] Cleanup for session {actual_session_id}")
        # Cleanup
        if actual_session_id and actual_session_id in active_connections:
            try:
                conn = active_connections[actual_session_id]
                if conn.get("state", {}).get("session"):
                    await conn["state"]["session"].close()
            except Exception as e:
                print(f"[WS] Cleanup error: {e}")
            del active_connections[actual_session_id]


@router.websocket("/ws")
async def websocket_chat_new(websocket: WebSocket):
    """WebSocket endpoint for new session."""
    await websocket_chat(websocket, None)
