from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from urllib.request import Request, urlopen

from actuar_bridge.relay import ExtensionRelayService, ExtensionRelayState


@dataclass
class FakeClient:
    claimed_job: dict | None = None
    heartbeat_calls: int = 0
    claim_calls: int = 0
    completed: list[dict] = field(default_factory=list)
    failed: list[dict] = field(default_factory=list)

    def heartbeat(self):
        self.heartbeat_calls += 1
        return {"poll_interval_seconds": 1}

    def claim_job(self):
        self.claim_calls += 1
        return self.claimed_job

    def complete_job(self, job_id, *, external_id, action_log_json, note=None):
        self.completed.append(
            {
                "job_id": job_id,
                "external_id": external_id,
                "action_log_json": action_log_json,
                "note": note,
            }
        )

    def fail_job(self, job_id, *, error_code, error_message, retryable=False, manual_fallback=True, action_log_json=None):
        self.failed.append(
            {
                "job_id": job_id,
                "error_code": error_code,
                "error_message": error_message,
                "retryable": retryable,
                "manual_fallback": manual_fallback,
                "action_log_json": action_log_json,
            }
        )


def test_relay_claims_only_when_browser_is_attached():
    client = FakeClient(claimed_job={"job_id": "job-1"})
    state = ExtensionRelayState(client=client)

    state.poll_backend_once()
    assert state.next_job() is None
    assert client.claim_calls == 0

    state.update_browser_status(attached=True, tab_id=7, url="https://app.actuar.com/alunos")
    state.poll_backend_once()

    assert client.claim_calls == 1
    assert state.next_job()["job_id"] == "job-1"


def test_relay_complete_and_fail_clear_pending_jobs():
    client = FakeClient()
    state = ExtensionRelayState(client=client)
    state.update_browser_status(attached=True, tab_id=7, url="https://app.actuar.com/alunos")
    state.pending_job = {"job_id": "job-2"}

    state.complete_job("job-2", external_id="act-2", action_log_json=[{"event": "ok"}], note="saved")

    assert client.completed[0]["job_id"] == "job-2"
    assert state.next_job() is None

    state.pending_job = {"job_id": "job-3"}
    state.fail_job("job-3", error_code="actuar_form_changed", error_message="DOM mudou", action_log_json=[])

    assert client.failed[0]["job_id"] == "job-3"
    assert state.next_job() is None


def test_relay_http_server_exposes_status_and_job_endpoints():
    client = FakeClient()
    state = ExtensionRelayState(client=client)
    service = ExtensionRelayService(state=state, host="127.0.0.1", port=44789)
    thread = threading.Thread(target=service.run_forever, daemon=True)
    thread.start()
    try:
        _post_json("http://127.0.0.1:44789/v1/browser/status", {"attached": True, "tab_id": 9, "url": "https://app.actuar.com/alunos"})
        state.pending_job = {"job_id": "job-9", "member_name": "Erick Bedin"}

        status_payload = _get_json("http://127.0.0.1:44789/v1/status")
        assert status_payload["browser_attached"] is True
        assert status_payload["pending_job_id"] == "job-9"

        next_job = _get_json("http://127.0.0.1:44789/v1/jobs/next")
        assert next_job["job_id"] == "job-9"

        _post_json(
            "http://127.0.0.1:44789/v1/jobs/job-9/complete",
            {"external_id": "act-9", "action_log_json": [{"event": "filled"}], "note": "ok"},
        )
        assert client.completed[0]["job_id"] == "job-9"
    finally:
        service.stop()
        thread.join(timeout=2)


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:  # noqa: S310 - local loopback test helper
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=5) as response:  # noqa: S310 - local loopback test helper
        body = response.read().decode("utf-8")
        return json.loads(body) if body else {}
