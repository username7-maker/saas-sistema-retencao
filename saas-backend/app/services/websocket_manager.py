import asyncio
import json
import logging
from collections import defaultdict
from concurrent.futures import Future
from typing import Any

from fastapi import WebSocket

from app.core.config import settings

try:
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - redis package missing
    Redis = None  # type: ignore[assignment,misc]
    AsyncRedis = None  # type: ignore[assignment,misc]

    class RedisError(Exception):
        pass


logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(
        self,
        *,
        redis_url: str = "",
        channel_name: str = "aigymos:websocket:events",
    ) -> None:
        self._connections: dict[str, dict[WebSocket, str | None]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._redis_url = redis_url
        self._channel_name = channel_name
        self._publisher: Redis | None = None
        self._publisher_enabled = False
        self._listener_task: asyncio.Task[None] | None = None
        self._load_publisher()

    def _load_publisher(self) -> None:
        if not self._redis_url or Redis is None:
            return
        try:
            client = Redis.from_url(self._redis_url, decode_responses=True)  # type: ignore[union-attr]
            client.ping()
            self._publisher = client
            self._publisher_enabled = True
            logger.info("WebSocket Redis publisher enabled.")
        except Exception:
            logger.exception("Failed to enable WebSocket Redis publisher. Falling back to local delivery only.")
            self._publisher = None
            self._publisher_enabled = False

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop
        if self._listener_task is None and self._redis_url and AsyncRedis is not None:
            self._listener_task = loop.create_task(self._run_pubsub_listener())

    def clear_event_loop(self) -> None:
        if self._listener_task is not None:
            self._listener_task.cancel()
            self._listener_task = None
        self._event_loop = None

    async def connect(self, gym_id: str, websocket: WebSocket, user_id: str | None = None) -> None:
        async with self._lock:
            self._connections[gym_id][websocket] = user_id

    async def disconnect(self, gym_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if gym_id in self._connections:
                self._connections[gym_id].pop(websocket, None)
                if not self._connections[gym_id]:
                    self._connections.pop(gym_id, None)

    async def broadcast_event(
        self,
        gym_id: str,
        event: str,
        payload: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> None:
        message = self._build_message(gym_id, event, payload, user_id=user_id)
        if self._publisher_enabled and self._publisher is not None:
            try:
                await asyncio.to_thread(self._publish_message, message)
                if self._listener_task is None:
                    await self._deliver_local(message)
                return
            except Exception:
                logger.exception(
                    "Failed publishing websocket message through Redis; falling back to local delivery.",
                    extra={"extra_fields": {"event": "websocket_publish_failed", "gym_id": gym_id, "ws_event": event}},
                )

        await self._deliver_local(message)

    def broadcast_event_sync(
        self,
        gym_id: str,
        event: str,
        payload: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> None:
        message = self._build_message(gym_id, event, payload, user_id=user_id)
        if self._publisher_enabled and self._publisher is not None:
            try:
                self._publish_message(message)
                return
            except Exception:
                logger.exception(
                    "Failed publishing websocket message through Redis from sync context.",
                    extra={"extra_fields": {"event": "websocket_publish_failed", "gym_id": gym_id, "ws_event": event}},
                )

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

        coroutine = self._deliver_local(message)
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

    def _build_message(
        self,
        gym_id: str,
        event: str,
        payload: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "gym_id": gym_id,
            "user_id": user_id,
            "event": event,
            "payload": payload,
        }

    def _publish_message(self, message: dict[str, Any]) -> None:
        if not self._publisher_enabled or self._publisher is None:
            raise RuntimeError("Redis websocket publisher unavailable")
        self._publisher.publish(
            self._channel_name,
            json.dumps(message, ensure_ascii=False, default=str),
        )

    async def _deliver_local(self, message: dict[str, Any]) -> None:
        gym_id = str(message["gym_id"])
        target_user_id = message.get("user_id")
        async with self._lock:
            stored_clients = self._connections.get(gym_id, {})
            if hasattr(stored_clients, "items"):
                clients = list(stored_clients.items())
            else:  # Backward compatibility for legacy tests mutating the internal structure.
                clients = [(client, None) for client in stored_clients]
        if not clients:
            return

        outbound = {"event": message["event"], "payload": message["payload"]}
        stale: list[WebSocket] = []
        for client, connected_user_id in clients:
            if target_user_id and connected_user_id != target_user_id:
                continue
            try:
                await client.send_json(outbound)
            except Exception:
                stale.append(client)

        if stale:
            logger.warning(
                "WebSocket broadcast pruned stale connections.",
                extra={
                    "extra_fields": {
                        "event": "websocket_broadcast_pruned",
                        "gym_id": gym_id,
                        "ws_event": message["event"],
                        "stale_connections": len(stale),
                    }
                },
            )
            async with self._lock:
                for client in stale:
                    current = self._connections.get(gym_id)
                    if current is None:
                        continue
                    if isinstance(current, dict):
                        current.pop(client, None)
                    else:
                        current.discard(client)
                if gym_id in self._connections and not self._connections[gym_id]:
                    self._connections.pop(gym_id, None)

    async def _run_pubsub_listener(self) -> None:
        if not self._redis_url or AsyncRedis is None:
            return

        redis: AsyncRedis | None = None
        pubsub = None
        try:
            redis = AsyncRedis.from_url(self._redis_url, decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe(self._channel_name)
            logger.info("WebSocket Redis subscriber started.")
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    try:
                        payload = json.loads(message["data"])
                    except (TypeError, ValueError, json.JSONDecodeError):
                        logger.warning("Ignoring malformed websocket pubsub payload.")
                    else:
                        await self._deliver_local(payload)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:  # pragma: no cover - lifecycle cleanup
            raise
        except Exception:
            logger.exception("WebSocket Redis subscriber stopped unexpectedly.")
        finally:
            if pubsub is not None:
                try:
                    await pubsub.close()
                except Exception:
                    logger.debug("Failed closing websocket pubsub cleanly.", exc_info=True)
            if redis is not None:
                try:
                    await redis.close()
                except Exception:
                    logger.debug("Failed closing websocket redis client cleanly.", exc_info=True)

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


websocket_manager = WebSocketManager(redis_url=settings.redis_url)
