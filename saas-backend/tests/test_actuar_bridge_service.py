import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.actuar_bridge_service import (
    _persist_member_link_from_bridge_success,
    authenticate_actuar_bridge_device,
    claim_next_actuar_bridge_job,
    heartbeat_actuar_bridge_device,
    issue_actuar_bridge_pairing_code,
    pair_actuar_bridge_device,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JOB_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
MEMBER_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
EVALUATION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _device(status: str = "pairing") -> SimpleNamespace:
    return SimpleNamespace(
        id=DEVICE_ID,
        gym_id=GYM_ID,
        device_name="Bridge Sala 1",
        status=status,
        pairing_code_hash=None,
        pairing_code_expires_at=None,
        auth_token_hash=None,
        bridge_version="0.1.0",
        browser_name="Chrome",
        paired_at=None,
        last_seen_at=None,
        last_job_claimed_at=None,
        last_job_completed_at=None,
        last_error_code=None,
        last_error_message=None,
        revoked_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_issue_pairing_code_creates_pending_device():
    db = MagicMock()

    with patch("app.services.actuar_bridge_service._generate_pairing_code", return_value="ABCD-1234"):
        result = issue_actuar_bridge_pairing_code(
            db,
            gym_id=GYM_ID,
            created_by_user_id=uuid.UUID("66666666-6666-6666-6666-666666666666"),
        )

    assert result.pairing_code == "ABCD-1234"
    assert result.device_id is not None
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_pair_device_returns_long_lived_token():
    db = MagicMock()
    device = _device(status="pairing")
    db.scalar.return_value = device

    with patch("app.services.actuar_bridge_service.secrets.token_urlsafe", return_value="bridge-token-123"):
        result = pair_actuar_bridge_device(
            db,
            payload=SimpleNamespace(
                pairing_code="ABCD-1234",
                device_name="Notebook Recepcao",
                bridge_version="0.1.0",
                browser_name="Edge",
            ),
        )

    assert result.device_token == "bridge-token-123"
    assert result.device.device_name == "Notebook Recepcao"
    assert device.status == "offline"
    assert device.auth_token_hash is not None


def test_authenticate_device_rejects_unknown_token():
    db = MagicMock()
    db.scalar.return_value = None

    with patch("app.services.actuar_bridge_service._hash_secret", return_value="hash"), patch(
        "app.services.actuar_bridge_service.include_all_tenants", side_effect=lambda stmt, reason: stmt
    ):
        try:
            authenticate_actuar_bridge_device(db, device_token="invalid")
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "status_code", None) == 401
        else:
            raise AssertionError("authenticate_actuar_bridge_device should reject invalid token")


def test_heartbeat_marks_device_online():
    db = MagicMock()
    device = _device(status="offline")

    result = heartbeat_actuar_bridge_device(db, device=device, bridge_version="0.2.0", browser_name="Chrome")

    assert result.device.status == "online"
    assert device.status == "online"
    assert device.bridge_version == "0.2.0"
    assert device.last_seen_at is not None


def test_claim_next_bridge_job_starts_attempt_and_returns_payload():
    db = MagicMock()
    device = _device(status="online")
    job = SimpleNamespace(
        id=JOB_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        body_composition_evaluation_id=EVALUATION_ID,
        status="pending",
        created_at=datetime.now(timezone.utc),
        payload_json={"weight": 84.5},
        mapped_fields_json={"mapped_fields": [{"field": "weight_kg", "actuar_field": "weight", "value": 84.5}]},
        critical_fields_json=[{"field": "weight_kg"}],
        non_critical_fields_json=[],
        retry_count=0,
        max_retries=3,
        next_retry_at=None,
        locked_at=None,
        locked_by=None,
    )
    evaluation = SimpleNamespace(id=EVALUATION_ID, actuar_sync_mode="local_bridge")
    member = SimpleNamespace(id=MEMBER_ID, full_name="Aluno Ponte", email="aluno.ponte@example.com", birthdate=None, cpf_encrypted=None)
    link = SimpleNamespace(actuar_search_document="12345678900", actuar_external_id="act-1")

    select_result = MagicMock()
    select_result.first.return_value = (job, evaluation, member, link)
    update_result = MagicMock()
    update_result.rowcount = 1
    db.execute.side_effect = [select_result, update_result]

    with patch("app.services.actuar_bridge_service._start_bridge_attempt") as start_attempt, patch(
        "app.services.actuar_bridge_service.build_manual_sync_summary",
        return_value={"summary_text": "Resumo manual"},
    ):
        claimed = claim_next_actuar_bridge_job(db, device=device)

    assert claimed is not None
    assert claimed.job_id == JOB_ID
    assert claimed.member_name == "Aluno Ponte"
    assert claimed.member_email == "aluno.ponte@example.com"
    assert claimed.member_document == "12345678900"
    assert claimed.manual_summary_text == "Resumo manual"
    start_attempt.assert_called_once()


def test_persist_member_link_updates_existing_row_without_reinserting():
    db = MagicMock()
    job = SimpleNamespace(gym_id=GYM_ID, member_id=MEMBER_ID)
    member = SimpleNamespace(id=MEMBER_ID, full_name="Aluno Ponte", birthdate=None, cpf_encrypted=None)
    current_link = SimpleNamespace(
        actuar_external_id="act-old",
        actuar_search_name="Aluno Ponte",
        actuar_search_document="12345678900",
        actuar_search_birthdate=None,
        linked_at=None,
        linked_by_user_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
        match_confidence=0.4,
        is_active=False,
    )

    with patch("app.services.actuar_bridge_service.include_all_tenants", side_effect=lambda stmt, reason: stmt), patch(
        "app.services.actuar_bridge_service.get_actuar_member_link",
        return_value=current_link,
    ), patch(
        "app.services.actuar_bridge_service.resolve_member_document_for_actuar",
        return_value="12345678900",
    ), patch(
        "app.services.actuar_bridge_service.upsert_actuar_member_link",
    ) as upsert_link:
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = member
        db.scalar.return_value = member
        _persist_member_link_from_bridge_success(db, job=job, external_id="act-new")

    assert current_link.actuar_external_id == "act-new"
    assert current_link.is_active is True
    assert current_link.match_confidence == 1.0
    db.flush.assert_called_once()
    upsert_link.assert_not_called()
