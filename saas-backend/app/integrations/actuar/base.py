from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ActuarSyncOutcome:
    status: str
    provider: str
    external_id: str | None = None
    error: str | None = None
    payload_snapshot_json: dict[str, Any] | list[Any] | None = None


class ActuarBodyCompositionProvider(ABC):
    provider_name: str
    sync_mode: str

    @abstractmethod
    def push_body_composition(self, payload: dict[str, Any]) -> ActuarSyncOutcome:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        raise NotImplementedError

    def export_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return payload
