import asyncio
import logging
from collections import defaultdict
from concurrent.futures import Future
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._event_loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop

    def clear_event_loop(self) -> None:
        self._event_loop = None

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
            logger.warning(
                "WebSocket broadcast pruned stale connections.",
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_pruned",
                        "gym_id": gym_id,
                        "ws_event": event,
                        "stale_connections": len(stale),
                    }
                },
            )
            async with self._lock:
                for client in stale:
                    self._connections[gym_id].discard(client)
                if not self._connections[gym_id]:
                    self._connections.pop(gym_id, None)

    def broadcast_event_sync(self, gym_id: str, event: str, payload: dict[str, Any]) -> None:
        loop = self._event_loop
        if loop is None or loop.is_closed() or not loop.is_running():
            logger.error(
                "WebSocket broadcast requested without an available event loop.",
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_unavailable",
                        "gym_id": gym_id,
                        "ws_event": event,
                    }
                },
            )
            return

        coroutine = self.broadcast_event(gym_id, event, payload)
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        try:
            if running_loop is loop:
                task = loop.create_task(coroutine)
                self._attach_completion_logging(task, gym_id=gym_id, event=event)
                return

            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            self._attach_completion_logging(future, gym_id=gym_id, event=event)
        except Exception:
            coroutine.close()
            logger.exception(
                "Failed scheduling websocket broadcast from sync context.",
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_failed",
                        "gym_id": gym_id,
                        "ws_event": event,
                    }
                },
            )

    def _attach_completion_logging(
        self,
        handle: asyncio.Task[None] | Future[None],
        *,
        gym_id: str,
        event: str,
    ) -> None:
        handle.add_done_callback(
            lambda future: self._log_broadcast_failure(future, gym_id=gym_id, event=event)
        )

    def _log_broadcast_failure(
        self,
        future: asyncio.Task[None] | Future[None],
        *,
        gym_id: str,
        event: str,
    ) -> None:
        try:
            if future.cancelled():
                logger.error(
                    "WebSocket broadcast task was cancelled.",
                    extra={
                        "extra_fields": {
                            "event": "websocket_broadcast_failed",
                            "gym_id": gym_id,
                            "ws_event": event,
                            "status": "cancelled",
                        }
                    },
                )
                return
            exc = future.exception()
        except Exception:
            logger.exception(
                "Failed retrieving websocket broadcast task result.",
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_failed",
                        "gym_id": gym_id,
                        "ws_event": event,
                    }
                },
            )
            return

        if exc is not None:
            logger.error(
                "WebSocket broadcast task failed.",
                exc_info=(type(exc), exc, exc.__traceback__),
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_failed",
                        "gym_id": gym_id,
                        "ws_event": event,
                    }
                },
            )


websocket_manager = WebSocketManager()
