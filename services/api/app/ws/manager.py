"""The event bus behind /ws/events. Phase 1 only wires the connection itself
(PROMPT.md §13 step 5: "green WebSocket badge"); domain events start flowing
once Phase 3/4 features exist to emit them.
"""

import json

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        # jsonable_encoder, not raw json.dumps -- payloads carry datetimes,
        # enums, etc. straight from the ORM (see Document.uploaded_at).
        message = json.dumps(jsonable_encoder({"type": event_type, "payload": payload}))
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
