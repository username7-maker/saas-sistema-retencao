from __future__ import annotations

from app.integrations.actuar.browser_client import ActuarPlaywrightProvider


class ActuarAssistedRpaProvider(ActuarPlaywrightProvider):
    provider_name = "actuar_assisted_rpa"
    sync_mode = "assisted_rpa"
