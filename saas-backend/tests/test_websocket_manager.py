import asyncio
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from app.services.websocket_manager import WebSocketManager


class _HealthyWebSocket:
    def __init__(self) -> None:
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class _BrokenWebSocket:
    async def send_json(self, message):
        raise RuntimeError("broken websocket")


def test_broadcast_event_sync_logs_when_loop_is_unavailable(caplog):
    manager = WebSocketManager()

    with caplog.at_level("ERROR"):
        manager.broadcast_event_sync("gym-1", "risk_processing_complete", {"members_analyzed": 10})

    assert any(
        getattr(record, "extra_fields", {}).get("event") == "websocket_broadcast_unavailable"
        for record in caplog.records
    )


def test_broadcast_event_sync_uses_run_coroutine_threadsafe_outside_loop():
    manager = WebSocketManager()
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.return_value = True
    manager.set_event_loop(loop)

    future = MagicMock(spec=Future)

    def _schedule(coro, target_loop):
        assert asyncio.iscoroutine(coro)
        assert target_loop is loop
        coro.close()
        return future

    with patch("app.services.websocket_manager.asyncio.get_running_loop", side_effect=RuntimeError), patch(
        "app.services.websocket_manager.asyncio.run_coroutine_threadsafe",
        side_effect=_schedule,
    ) as run_coroutine_threadsafe:
        manager.broadcast_event_sync("gym-1", "risk_processing_complete", {"members_analyzed": 10})

    run_coroutine_threadsafe.assert_called_once()
    future.add_done_callback.assert_called_once()


def test_broadcast_event_sync_logs_async_delivery_failure(caplog):
    manager = WebSocketManager()
    loop = MagicMock()
    loop.is_closed.return_value = False
    loop.is_running.return_value = True
    manager.set_event_loop(loop)

    future = MagicMock(spec=Future)
    future.cancelled.return_value = False
    future.exception.return_value = RuntimeError("boom")

    def _schedule(coro, target_loop):
        coro.close()
        return future

    def _attach_and_run(callback):
        callback(future)
        return None

    future.add_done_callback.side_effect = _attach_and_run

    with caplog.at_level("ERROR"), patch(
        "app.services.websocket_manager.asyncio.get_running_loop", side_effect=RuntimeError
    ), patch(
        "app.services.websocket_manager.asyncio.run_coroutine_threadsafe",
        side_effect=_schedule,
    ):
        manager.broadcast_event_sync("gym-1", "risk_processing_complete", {"members_analyzed": 10})

    assert any(
        getattr(record, "extra_fields", {}).get("event") == "websocket_broadcast_failed"
        for record in caplog.records
    )


def test_broadcast_event_sends_and_prunes_stale_connections(caplog):
    manager = WebSocketManager()
    healthy = _HealthyWebSocket()
    broken = _BrokenWebSocket()
    manager._connections["gym-1"] = {healthy, broken}

    with caplog.at_level("WARNING"):
        asyncio.run(manager.broadcast_event("gym-1", "risk_processing_complete", {"members_analyzed": 10}))

    assert healthy.messages == [
        {
            "event": "risk_processing_complete",
            "payload": {"members_analyzed": 10},
        }
    ]
    assert manager._connections["gym-1"] == {healthy}
    assert any(
        getattr(record, "extra_fields", {}).get("event") == "websocket_broadcast_pruned"
        for record in caplog.records
    )
