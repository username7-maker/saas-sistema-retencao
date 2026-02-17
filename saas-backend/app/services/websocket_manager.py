import asyncio
from collections import defaultdict
from typing import Any

import anyio
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, gym_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[gym_id].add(websocket)

    async def disconnect(self, gym_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if gym_id in self._connections:
                self._connections[gym_id].discard(websocket)
                if not self._connections[gym_id]:
                    self._connections.pop(gym_id, None)

    async def broadcast_event(self, gym_id: str, event: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._connections.get(gym_id, set()))
        if not clients:
            return

        message = {"event": event, "payload": payload}
        stale: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                stale.append(client)

        if stale:
            async with self._lock:
                for client in stale:
                    self._connections[gym_id].discard(client)
                if not self._connections[gym_id]:
                    self._connections.pop(gym_id, None)

    def broadcast_event_sync(self, gym_id: str, event: str, payload: dict[str, Any]) -> None:
        try:
            anyio.from_thread.run(self.broadcast_event, gym_id, event, payload)
        except RuntimeError:
            # Called outside anyio worker context.
            pass


websocket_manager = WebSocketManager()
