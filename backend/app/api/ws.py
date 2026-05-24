import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


# -----------------------------------------------------------------------------
# Connection Manager — tracks every connected dashboard client
# This is a module-level singleton so subscriber.py and anomaly.py can import it
# -----------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        print(f"[WS] Client connected  — total: {len(self.active)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.remove(websocket)
        print(f"[WS] Client disconnected — total: {len(self.active)}")

    async def broadcast(self, event: str, data: dict) -> None:
        """Push an event to all connected dashboard clients."""
        if not self.active:
            return

        message = {"event": event, "data": data}
        dead = []

        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        # Clean up any connections that died mid-broadcast
        for ws in dead:
            self.active.remove(ws)


# Singleton — import this in subscriber.py and anomaly.py
manager = ConnectionManager()


# -----------------------------------------------------------------------------
# WebSocket endpoint
# Dashboard connects here: ws://localhost:8000/ws
# -----------------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Keep the connection open — just wait for the client to disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
