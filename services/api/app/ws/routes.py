from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.security import decode_access_token
from app.ws.manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer JWT — same token used for REST calls"),
) -> None:
    """Real-time event stream.

    The Flutter client appends ?token=<jwt> to the WebSocket URL before
    connecting. We verify it here before accepting so anonymous browsers
    cannot subscribe to the live feed of student names, attendance marks,
    and guardian phone numbers.

    Close code 1008 = Policy Violation (RFC 6455 §7.4.1) — the standard
    code for authentication/authorisation failure on WebSocket.
    """
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "payload": {}})
        while True:
            # No inbound protocol yet — keep alive and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
