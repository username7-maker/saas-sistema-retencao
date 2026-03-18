from __future__ import annotations

from app.core.config import settings
from app.integrations.actuar.base import ActuarBodyCompositionProvider, ActuarSyncOutcome


class ActuarHttpApiProvider(ActuarBodyCompositionProvider):
    provider_name = "actuar_http_api"
    sync_mode = "http_api"

    def push_body_composition(self, payload: dict) -> ActuarSyncOutcome:
        if not settings.actuar_base_url:
            return ActuarSyncOutcome(
                status="skipped",
                provider=self.provider_name,
                error="Modo http_api habilitado, mas ACTUAR_BASE_URL nao foi configurado.",
                payload_snapshot_json=self.export_payload(payload),
            )

        return ActuarSyncOutcome(
            status="skipped",
            provider=self.provider_name,
            error=(
                "Modo http_api habilitado, mas o contrato tecnico real da Actuar ainda nao foi "
                "mapeado. Provider preparado sem endpoint inventado."
            ),
            payload_snapshot_json=self.export_payload(payload),
        )

    def test_connection(self) -> dict:
        return {
            "provider": self.provider_name,
            "supported": False,
            "reason": "Contrato tecnico da Actuar nao configurado para http_api.",
        }
