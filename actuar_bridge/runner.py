from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from actuar_bridge.bridge_client import BridgeClient
from actuar_bridge.executor import BridgeExecutionResult, BridgeExecutor


@dataclass(slots=True)
class ActuarBridgeRunner:
    client: BridgeClient
    executor: BridgeExecutor
    idle_sleep_seconds: int = 5

    def run_cycle(self) -> str:
        heartbeat = self.client.heartbeat()
        poll_interval = int(heartbeat.get("poll_interval_seconds") or self.idle_sleep_seconds)
        job = self.client.claim_job()
        if not job:
            sleep(max(poll_interval, 1))
            return "idle"

        result = self.executor.execute(job)
        if result.succeeded:
            self.client.complete_job(
                str(job["job_id"]),
                external_id=result.external_id,
                action_log_json=result.action_log,
            )
            return "completed"

        self.client.fail_job(
            str(job["job_id"]),
            error_code=result.error_code or "bridge_execution_failed",
            error_message=result.error_message or "A estacao local falhou ao executar o job do Actuar.",
            retryable=result.retryable,
            manual_fallback=result.manual_fallback,
            action_log_json=result.action_log,
        )
        return "failed"

    def run_forever(self) -> None:
        while True:
            self.run_cycle()
