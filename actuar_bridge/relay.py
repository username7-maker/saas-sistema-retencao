from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import sleep
from typing import Any
from urllib.parse import urlparse

import httpx

from actuar_bridge.bridge_client import BridgeClient


def _job_id(job: dict[str, Any] | None) -> str | None:
    if not job:
        return None
    value = job.get("job_id")
    return str(value) if value is not None else None


@dataclass(slots=True)
class RelayBrowserStatus:
    attached: bool = False
    tab_id: int | None = None
    url: str | None = None
    title: str | None = None


@dataclass(slots=True)
class ExtensionRelayState:
    client: BridgeClient
    idle_sleep_seconds: int = 3
    browser: RelayBrowserStatus = field(default_factory=RelayBrowserStatus)
    pending_job: dict[str, Any] | None = None
    pending_job_dispatched: bool = False
    poll_interval_seconds: int = 15
    last_error: str | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    def update_browser_status(
        self,
        *,
        attached: bool,
        tab_id: int | None = None,
        url: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self.browser = RelayBrowserStatus(attached=attached, tab_id=tab_id, url=url, title=title)
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "browser_attached": self.browser.attached,
                "browser_tab_id": self.browser.tab_id,
                "browser_url": self.browser.url,
                "browser_title": self.browser.title,
                "pending_job_id": _job_id(self.pending_job),
                "pending_job": self.pending_job,
                "pending_job_dispatched": self.pending_job_dispatched,
                "poll_interval_seconds": self.poll_interval_seconds,
                "last_error": self.last_error,
            }

    def poll_backend_once(self) -> dict[str, Any]:
        with self._lock:
            if not self.browser.attached:
                self.poll_interval_seconds = max(self.idle_sleep_seconds, 1)
                return self.snapshot()
            if self.pending_job is not None:
                return self.snapshot()

        heartbeat = self.client.heartbeat()
        poll_interval = int(heartbeat.get("poll_interval_seconds") or self.idle_sleep_seconds)
        with self._lock:
            self.poll_interval_seconds = max(poll_interval, 1)
            if self.pending_job is not None:
                return self.snapshot()
        try:
            job = self.client.claim_job()
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.last_error = str(exc)
                return self.snapshot()

        if job:
            with self._lock:
                self.pending_job = job
                self.pending_job_dispatched = False
                self.last_error = None
        return self.snapshot()

    def next_job(self) -> dict[str, Any] | None:
        with self._lock:
            if not self.browser.attached or self.pending_job is None or self.pending_job_dispatched:
                return None
            self.pending_job_dispatched = True
            return dict(self.pending_job)

    def complete_job(self, job_id: str, *, external_id: str | None, action_log_json: list[dict] | list | None, note: str | None = None) -> None:
        with self._lock:
            current = self.pending_job
            if _job_id(current) != str(job_id):
                raise ValueError("pending_job_mismatch")
        try:
            self.client.complete_job(job_id, external_id=external_id, action_log_json=action_log_json, note=note)
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            with self._lock:
                if status_code in {HTTPStatus.NOT_FOUND, HTTPStatus.CONFLICT}:
                    self.pending_job = None
                    self.pending_job_dispatched = False
                    self.last_error = None
                    return
                self.pending_job_dispatched = True
                self.last_error = str(exc)
            raise
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.pending_job_dispatched = True
                self.last_error = str(exc)
            raise
        with self._lock:
            self.pending_job = None
            self.pending_job_dispatched = False
            self.last_error = None

    def fail_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_message: str,
        retryable: bool = False,
        manual_fallback: bool = True,
        action_log_json: list[dict] | list | None = None,
    ) -> None:
        with self._lock:
            current = self.pending_job
            if _job_id(current) != str(job_id):
                raise ValueError("pending_job_mismatch")
        try:
            self.client.fail_job(
                job_id,
                error_code=error_code,
                error_message=error_message,
                retryable=retryable,
                manual_fallback=manual_fallback,
                action_log_json=action_log_json,
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            with self._lock:
                if status_code in {HTTPStatus.NOT_FOUND, HTTPStatus.CONFLICT}:
                    self.pending_job = None
                    self.pending_job_dispatched = False
                    self.last_error = error_message
                    return
                self.pending_job_dispatched = True
                self.last_error = str(exc)
            raise
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.pending_job_dispatched = True
                self.last_error = str(exc)
            raise
        with self._lock:
            self.pending_job = None
            self.pending_job_dispatched = False
            self.last_error = error_message


class ExtensionRelayService:
    def __init__(
        self,
        *,
        state: ExtensionRelayState,
        host: str = "127.0.0.1",
        port: int = 44777,
    ) -> None:
        self.state = state
        self.host = host
        self.port = port
        self._stop_event = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._httpd: ThreadingHTTPServer | None = None

    def run_forever(self) -> None:
        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.timeout = 0.5
        self._httpd.bridge_state = self.state  # type: ignore[attr-defined]
        self._stop_event.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, name="actuar-bridge-relay-poll", daemon=True)
        self._poll_thread.start()
        try:
            while not self._stop_event.is_set():
                self._httpd.handle_request()
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop_event.set()
        if self._httpd is not None:
            try:
                self._httpd.server_close()
            except OSError:
                pass
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            self.state.poll_backend_once()
            sleep(max(self.state.poll_interval_seconds, 1))

    def _build_handler(self):
        class RelayHandler(BaseHTTPRequestHandler):
            server_version = "ActuarBridgeRelay/0.1"

            @property
            def relay_state(self) -> ExtensionRelayState:
                return self.server.bridge_state  # type: ignore[attr-defined]

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(HTTPStatus.NO_CONTENT)
                self._write_cors_headers()
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path == "/health":
                    self._json_response(HTTPStatus.OK, {"ok": True, **self.relay_state.snapshot()})
                    return
                if parsed.path == "/v1/status":
                    self._json_response(HTTPStatus.OK, self.relay_state.snapshot())
                    return
                if parsed.path == "/v1/jobs/next":
                    job = self.relay_state.next_job()
                    if not job:
                        self._empty_response(HTTPStatus.NO_CONTENT)
                        return
                    self._json_response(HTTPStatus.OK, job)
                    return
                self._json_response(HTTPStatus.NOT_FOUND, {"detail": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                payload = self._read_json()
                if parsed.path == "/v1/browser/status":
                    snapshot = self.relay_state.update_browser_status(
                        attached=bool(payload.get("attached")),
                        tab_id=_int_or_none(payload.get("tab_id")),
                        url=_str_or_none(payload.get("url")),
                        title=_str_or_none(payload.get("title")),
                    )
                    self._json_response(HTTPStatus.OK, snapshot)
                    return

                if parsed.path.endswith("/complete") and parsed.path.startswith("/v1/jobs/"):
                    job_id = parsed.path.split("/")[3]
                    try:
                        self.relay_state.complete_job(
                            job_id,
                            external_id=_str_or_none(payload.get("external_id")),
                            action_log_json=payload.get("action_log_json"),
                            note=_str_or_none(payload.get("note")),
                        )
                    except ValueError:
                        self._json_response(HTTPStatus.CONFLICT, {"detail": "pending_job_mismatch"})
                        return
                    except Exception as exc:  # noqa: BLE001
                        self._json_response(HTTPStatus.BAD_GATEWAY, {"detail": "bridge_complete_failed", "error": str(exc)})
                        return
                    self._json_response(HTTPStatus.OK, {"status": "ok"})
                    return

                if parsed.path.endswith("/fail") and parsed.path.startswith("/v1/jobs/"):
                    job_id = parsed.path.split("/")[3]
                    try:
                        self.relay_state.fail_job(
                            job_id,
                            error_code=str(payload.get("error_code") or "extension_failed"),
                            error_message=str(payload.get("error_message") or "Falha da extensao do navegador."),
                            retryable=bool(payload.get("retryable")),
                            manual_fallback=bool(payload.get("manual_fallback", True)),
                            action_log_json=payload.get("action_log_json"),
                        )
                    except ValueError:
                        self._json_response(HTTPStatus.CONFLICT, {"detail": "pending_job_mismatch"})
                        return
                    except Exception as exc:  # noqa: BLE001
                        self._json_response(HTTPStatus.BAD_GATEWAY, {"detail": "bridge_fail_failed", "error": str(exc)})
                        return
                    self._json_response(HTTPStatus.OK, {"status": "ok"})
                    return

                self._json_response(HTTPStatus.NOT_FOUND, {"detail": "not_found"})

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return None

            def _read_json(self) -> dict[str, Any]:
                content_length = int(self.headers.get("Content-Length", "0") or "0")
                if content_length <= 0:
                    return {}
                raw = self.rfile.read(content_length)
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))

            def _empty_response(self, status_code: HTTPStatus) -> None:
                self.send_response(status_code)
                self._write_cors_headers()
                self.end_headers()

            def _json_response(self, status_code: HTTPStatus, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self._write_cors_headers()
                self.end_headers()
                self.wfile.write(body)

            def _write_cors_headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

        return RelayHandler


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
