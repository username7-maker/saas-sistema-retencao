from __future__ import annotations

from app.integrations.actuar.base import ActuarBodyCompositionProvider, ActuarSyncOutcome


class ActuarCsvExportProvider(ActuarBodyCompositionProvider):
    provider_name = "actuar_csv_export"
    sync_mode = "csv_export"

    def push_body_composition(self, payload: dict) -> ActuarSyncOutcome:
        snapshot = self.export_payload(payload)
        external_id = f"csv-export:{payload.get('evaluation_id')}"
        return ActuarSyncOutcome(
            status="exported",
            provider=self.provider_name,
            external_id=external_id,
            payload_snapshot_json=snapshot,
        )

    def test_connection(self) -> dict:
        return {
            "provider": self.provider_name,
            "supported": True,
            "mode": self.sync_mode,
        }
