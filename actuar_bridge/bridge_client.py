from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class BridgeClient:
    api_base_url: str
    device_token: str | None = None
    timeout_seconds: int = 20

    def __post_init__(self) -> None:
        self.api_base_url = self.api_base_url.rstrip("/")

    def pair(self, *, pairing_code: str, device_name: str, bridge_version: str | None, browser_name: str | None) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base_url}/api/v1/actuar-bridge/pair",
                json={
                    "pairing_code": pairing_code,
                    "device_name": device_name,
                    "bridge_version": bridge_version,
                    "browser_name": browser_name,
                },
            )
            response.raise_for_status()
            payload = response.json()
            self.device_token = payload["device_token"]
            return payload

    def heartbeat(self) -> dict[str, Any]:
        response = self._post("/api/v1/actuar-bridge/heartbeat", json={})
        return response.json()

    def claim_job(self) -> dict[str, Any] | None:
        response = self._post("/api/v1/actuar-bridge/jobs/claim", json={})
        if response.status_code == 204 or response.text.strip() in {"", "null"}:
            return None
        payload = response.json()
        return payload or None

    def complete_job(self, job_id: str, *, external_id: str | None, action_log_json: list[dict] | list | None, note: str | None = None) -> None:
        self._post(
            f"/api/v1/actuar-bridge/jobs/{job_id}/complete",
            json={"external_id": external_id, "action_log_json": action_log_json, "note": note},
        )

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
        self._post(
            f"/api/v1/actuar-bridge/jobs/{job_id}/fail",
            json={
                "error_code": error_code,
                "error_message": error_message,
                "retryable": retryable,
                "manual_fallback": manual_fallback,
                "action_log_json": action_log_json,
            },
        )

    def _post(self, path: str, *, json: dict[str, Any]) -> httpx.Response:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.api_base_url}{path}",
                json=json,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.device_token:
            headers["X-Actuar-Bridge-Token"] = self.device_token
        return headers
