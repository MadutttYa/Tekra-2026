import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        print(f"[WS] Client connected — total: {len(self.active)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.remove(websocket)
        print(f"[WS] Client disconnected — total: {len(self.active)}")

    async def broadcast(self, event: str, data: dict) -> None:
        if not self.active:
            return
        message = {"event": event, "data": data}
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
