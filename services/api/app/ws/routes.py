from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "payload": {}})
        while True:
            # No inbound protocol yet — just keep the connection alive and
            # detect disconnects. Domain events are pushed via manager.broadcast().
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
