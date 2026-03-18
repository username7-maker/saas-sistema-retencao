from __future__ import annotations

from app.integrations.actuar.base import ActuarBodyCompositionProvider, ActuarSyncOutcome


class ActuarAssistedRpaProvider(ActuarBodyCompositionProvider):
    provider_name = "actuar_assisted_rpa"
    sync_mode = "assisted_rpa"

    def push_body_composition(self, payload: dict) -> ActuarSyncOutcome:
        return ActuarSyncOutcome(
            status="failed",
            provider=self.provider_name,
            error=(
                "Modo assisted_rpa ainda nao suportado nesta entrega. Estrutura preparada sem "
                "automacao fragil silenciosa."
            ),
            payload_snapshot_json=self.export_payload(payload),
        )

    def test_connection(self) -> dict:
        return {
            "provider": self.provider_name,
            "supported": False,
            "reason": "assisted_rpa nao implementado nesta entrega.",
        }
