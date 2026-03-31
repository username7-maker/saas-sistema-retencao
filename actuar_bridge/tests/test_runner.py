from types import SimpleNamespace

from actuar_bridge.executor import BridgeExecutionResult
from actuar_bridge.runner import ActuarBridgeRunner


class FakeClient:
    def __init__(self, job=None):
        self.job = job
        self.completed = None
        self.failed = None

    def heartbeat(self):
        return {"poll_interval_seconds": 1}

    def claim_job(self):
        return self.job

    def complete_job(self, job_id, *, external_id, action_log_json, note=None):
        self.completed = {"job_id": job_id, "external_id": external_id, "action_log_json": action_log_json, "note": note}

    def fail_job(self, job_id, *, error_code, error_message, retryable=False, manual_fallback=True, action_log_json=None):
        self.failed = {
            "job_id": job_id,
            "error_code": error_code,
            "error_message": error_message,
            "retryable": retryable,
            "manual_fallback": manual_fallback,
            "action_log_json": action_log_json,
        }


class FakeExecutor:
    def __init__(self, result: BridgeExecutionResult):
        self.result = result

    def execute(self, job):
        return self.result


def test_runner_completes_claimed_job():
    client = FakeClient(job={"job_id": "job-1"})
    runner = ActuarBridgeRunner(
        client=client,
        executor=FakeExecutor(BridgeExecutionResult(succeeded=True, external_id="act-1", action_log=[{"event": "ok"}])),
    )

    outcome = runner.run_cycle()

    assert outcome == "completed"
    assert client.completed["job_id"] == "job-1"
    assert client.failed is None


def test_runner_reports_failed_job():
    client = FakeClient(job={"job_id": "job-2"})
    runner = ActuarBridgeRunner(
        client=client,
        executor=FakeExecutor(
            BridgeExecutionResult(
                succeeded=False,
                error_code="actuar_tab_not_found",
                error_message="Aba nao encontrada",
                retryable=False,
                manual_fallback=True,
            )
        ),
    )

    outcome = runner.run_cycle()

    assert outcome == "failed"
    assert client.failed["job_id"] == "job-2"
    assert client.completed is None
