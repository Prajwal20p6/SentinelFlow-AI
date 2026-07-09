"""
SentinelFlow AI — WebSocket API Router
Exposes the authenticated /ws/{session_id} route.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Path
from ..core.database import SessionLocal
from ..models.models import User
from ..core.security import decode_token
from ..core.observability import logger
from ..websocket.manager import ws_connection_manager
from ..websocket.handlers import handle_client_message

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/{session_id}")
async def websocket_session_endpoint(
    websocket: WebSocket,
    session_id: str = Path(...),
    token: str = Query(None)
):
    """
    WebSocket endpoint. Authenticates via JWT token query param.
    Manages incoming client message parsing and connection lifecycles.
    """
    # 1. Fallback: Check header auth if query token is None
    if not token:
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    # 2. Deny connection if no token credentials present
    if not token:
        await websocket.accept()
        await websocket.close(code=4008, reason="Authentication token missing")
        return

    # 3. Authenticate JWT token
    try:
        payload = decode_token(token)
        email = payload.get("sub")
    except Exception as err:
        logger.error(f"WebSocket JWT handshake decode failed: {err}")
        await websocket.accept()
        await websocket.close(code=4008, reason="Could not validate credentials token")
        return

    # 4. Retrieve User record
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
    finally:
        db.close()

    if not user:
        await websocket.accept()
        await websocket.close(code=4008, reason="User account not found")
        return

    # 5. Connect session to ConnectionManager (enforces concurrency rate-limits)
    try:
        await ws_connection_manager.connect(websocket, user.id, session_id)
    except Exception as conn_err:
        logger.error(f"WS connection acceptance failed: {conn_err}")
        return

    # 6. Socket processing message loop
    try:
        while True:
            # Block and wait for incoming frames
            data = await websocket.receive_text()
            await handle_client_message(session_id, data)
    except WebSocketDisconnect:
        # Handles connection loss or clean client teardowns
        ws_connection_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket session '{session_id}' encountered error: {e}")
        ws_connection_manager.disconnect(session_id)
