import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum
from app.schemas.body_composition import BodyCompositionActuarSyncStatusRead


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVALUATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _current_user(role: RoleEnum) -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        role=role,
        is_active=True,
        deleted_at=None,
    )


def _sync_status_payload() -> BodyCompositionActuarSyncStatusRead:
    return BodyCompositionActuarSyncStatusRead.model_validate(
        {
            "evaluation_id": EVALUATION_ID,
            "member_id": MEMBER_ID,
            "sync_mode": "assisted_rpa",
            "sync_status": "synced_to_actuar",
            "training_ready": True,
            "sync_required_for_training": True,
            "external_id": "act-123",
            "last_synced_at": None,
            "last_attempt_at": None,
            "last_error_code": None,
            "last_error": None,
            "can_retry": False,
            "critical_fields": [],
            "fallback_manual_summary": {
                "evaluation_id": EVALUATION_ID,
                "member_id": MEMBER_ID,
                "sync_status": "synced_to_actuar",
                "training_ready": True,
                "critical_fields": [],
                "summary_text": "ok",
            },
            "current_job": None,
            "attempts": [],
            "member_link": None,
        }
    )


def test_manual_sync_confirm_requires_owner_or_manager(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.RECEPTIONIST)

    try:
        response = client.post(
            f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/manual-sync-confirm",
            json={"reason": "Lancado manualmente", "note": "sem bloqueio operacional"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Permissao insuficiente"


def test_manual_sync_confirm_logs_audit_and_returns_status(app, client):
    db = MagicMock()

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _current_user(RoleEnum.OWNER)

    with patch(
        "app.routers.members.confirm_manual_actuar_sync",
        return_value=SimpleNamespace(id=EVALUATION_ID),
    ) as confirm_mock, patch(
        "app.routers.members.get_body_composition_sync_status",
        return_value=_sync_status_payload(),
    ) as status_mock, patch(
        "app.routers.members.log_audit_event",
    ) as audit_mock:
        try:
            response = client.post(
                f"/api/v1/members/{MEMBER_ID}/body-composition/{EVALUATION_ID}/manual-sync-confirm",
                json={"reason": "Lancado manualmente", "note": "sem bloqueio operacional"},
            )
        finally:
            app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["training_ready"] is True
    confirm_mock.assert_called_once()
    status_mock.assert_called_once()
    audit_mock.assert_called_once()
    db.commit.assert_called_once()
