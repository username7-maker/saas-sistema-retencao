import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.actuar_sync import ActuarSyncJob
from app.integrations.actuar.base import ActuarSyncOutcome
from app.services.actuar_member_link_service import ActuarMemberResolution
from app.services.body_composition_actuar_mapping_service import build_actuar_field_mapping, build_manual_sync_summary
from app.services.body_composition_actuar_sync_service import (
    ActuarSyncServiceError,
    _build_provider,
    _finalize_non_browser_outcome,
    _finalize_sync_failure,
    _finalize_sync_success,
    claim_next_actuar_sync_job,
    confirm_manual_actuar_sync,
    get_body_composition_sync_status,
    prepare_body_composition_sync_attempt,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVALUATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
JOB_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
ATTEMPT_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


def _member() -> SimpleNamespace:
    return SimpleNamespace(
        id=MEMBER_ID,
        full_name="Aluno Sync",
        birthdate=date(1990, 1, 10),
        cpf_encrypted=None,
    )


def _evaluation(sync_status: str = "saved") -> SimpleNamespace:
    return SimpleNamespace(
        id=EVALUATION_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        evaluation_date=date(2026, 3, 23),
        weight_kg=84.5,
        body_fat_percent=23.0,
        fat_free_mass_kg=65.0,
        lean_mass_kg=65.0,
        skeletal_muscle_kg=35.0,
        muscle_mass_kg=35.0,
        body_water_percent=51.0,
        bmi=26.1,
        notes="Observacoes",
        source="manual",
        device_model="Tezewa",
        device_profile="tezewa_receipt_v1",
        measured_ranges_json=None,
        sync_required_for_training=True,
        actuar_sync_mode="disabled",
        actuar_sync_status=sync_status,
        actuar_external_id=None,
        actuar_last_synced_at=None,
        actuar_last_error=None,
        sync_last_attempt_at=None,
        sync_last_success_at=None,
        sync_last_error_code=None,
        sync_last_error_message=None,
        actuar_sync_job_id=None,
        training_ready=False,
    )


def _job(status: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(
        id=JOB_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        body_composition_evaluation_id=EVALUATION_ID,
        status=status,
        error_code=None,
        error_message=None,
        retry_count=0,
        max_retries=3,
        next_retry_at=None,
        locked_at=None,
        locked_by=None,
        synced_at=None,
    )


def _attempt() -> SimpleNamespace:
    return SimpleNamespace(
        id=ATTEMPT_ID,
        gym_id=GYM_ID,
        sync_job_id=JOB_ID,
        status="started",
        finished_at=None,
        action_log_json=None,
        screenshot_path=None,
        page_html_path=None,
        error_code=None,
        error_message=None,
    )


def test_prepare_sync_job_marks_pending_and_not_training_ready():
    db = MagicMock()
    gym = SimpleNamespace(id=GYM_ID, actuar_enabled=True, actuar_auto_sync_body_composition=True)
    member = _member()
    evaluation = _evaluation()

    with patch("app.services.body_composition_actuar_sync_service._get_gym", return_value=gym), patch(
        "app.services.body_composition_actuar_sync_service._cancel_superseded_jobs"
    ), patch("app.services.body_composition_actuar_sync_service.settings.actuar_sync_enabled", True), patch(
        "app.services.body_composition_actuar_sync_service.settings.actuar_sync_mode",
        "assisted_rpa",
    ), patch(
        "app.services.body_composition_actuar_sync_service.settings.actuar_sync_required_for_training",
        True,
    ), patch(
        "app.services.body_composition_actuar_sync_service.settings.actuar_sync_max_retries",
        3,
    ):
        job = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation)

    assert isinstance(job, ActuarSyncJob)
    assert job.status == "pending"
    assert evaluation.actuar_sync_status == "sync_pending"
    assert evaluation.sync_required_for_training is True
    assert evaluation.actuar_sync_mode == "assisted_rpa"
    assert evaluation.actuar_sync_job_id == job.id


def test_prepare_sync_job_keeps_saved_when_auto_sync_disabled():
    db = MagicMock()
    gym = SimpleNamespace(id=GYM_ID, actuar_enabled=False, actuar_auto_sync_body_composition=False)
    evaluation = _evaluation()

    with patch("app.services.body_composition_actuar_sync_service._get_gym", return_value=gym), patch(
        "app.services.body_composition_actuar_sync_service.settings.actuar_sync_enabled",
        True,
    ):
        job = prepare_body_composition_sync_attempt(db, member=_member(), evaluation=evaluation)

    assert job is None
    assert evaluation.actuar_sync_status == "saved"
    assert evaluation.actuar_sync_job_id is None


def test_existing_link_external_id_short_circuits_matching():
    db = MagicMock()
    link = SimpleNamespace(
        is_active=True,
        actuar_external_id="act-123",
        match_confidence=1,
    )
    provider = MagicMock()

    with patch("app.services.actuar_member_link_service.get_actuar_member_link", return_value=link):
        from app.services.actuar_member_link_service import resolve_actuar_member

        resolution = resolve_actuar_member(db, gym_id=GYM_ID, member=_member(), provider=provider)

    assert isinstance(resolution, ActuarMemberResolution)
    assert resolution.status == "matched"
    assert resolution.actuar_external_id == "act-123"
    provider.find_member.assert_not_called()


def test_ambiguous_match_returns_needs_review():
    db = MagicMock()
    provider = MagicMock()
    provider.find_member.side_effect = [{"status": "ambiguous", "error_code": "member_match_ambiguous"}]

    with patch("app.services.actuar_member_link_service.get_actuar_member_link", return_value=None):
        from app.services.actuar_member_link_service import resolve_actuar_member

        resolution = resolve_actuar_member(db, gym_id=GYM_ID, member=_member(), provider=provider)

    assert resolution.status == "needs_review"
    assert resolution.error_code == "member_match_ambiguous"


def test_member_not_found_keeps_resolution_for_review():
    db = MagicMock()
    provider = MagicMock()
    provider.find_member.side_effect = [
        {"status": "not_found", "error_code": "member_not_found"},
        {"status": "not_found", "error_code": "member_not_found"},
    ]

    with patch("app.services.actuar_member_link_service.get_actuar_member_link", return_value=None):
        from app.services.actuar_member_link_service import resolve_actuar_member

        resolution = resolve_actuar_member(db, gym_id=GYM_ID, member=_member(), provider=provider)

    assert resolution.status == "needs_review"
    assert resolution.error_code == "member_not_found"


def test_finalize_sync_success_marks_synced_and_training_ready():
    db = MagicMock()
    evaluation = _evaluation(sync_status="syncing")
    job = _job(status="processing")
    attempt = _attempt()

    _finalize_sync_success(
        db,
        job=job,
        evaluation=evaluation,
        attempt=attempt,
        external_id="act-123",
        action_log=[{"event": "filled"}],
        screenshot_path=None,
        page_html_path=None,
    )

    assert job.status == "synced"
    assert evaluation.actuar_sync_status == "synced_to_actuar"
    assert evaluation.actuar_external_id == "act-123"
    assert evaluation.sync_last_success_at is not None
    assert evaluation.actuar_last_error is None


def test_finalize_csv_export_marks_manual_sync_required_and_logs_snapshot():
    db = MagicMock()
    evaluation = _evaluation(sync_status="syncing")
    job = _job(status="processing")
    attempt = _attempt()

    _finalize_non_browser_outcome(
        db,
        job=job,
        evaluation=evaluation,
        attempt=attempt,
        outcome=ActuarSyncOutcome(
            status="exported",
            provider="actuar_csv_export",
            external_id="csv-export:4444",
            payload_snapshot_json={"evaluation_id": str(EVALUATION_ID), "weight_kg": 84.5},
        ),
    )

    assert attempt.status == "succeeded"
    assert job.status == "needs_review"
    assert job.error_code == "csv_export_ready"
    assert evaluation.actuar_sync_status == "manual_sync_required"
    assert evaluation.sync_last_error_code == "csv_export_ready"
    assert evaluation.actuar_external_id == "csv-export:4444"
    assert attempt.action_log_json[0]["event"] == "csv_export_ready"


def test_finalize_transient_failure_schedules_retry_and_keeps_not_ready():
    db = MagicMock()
    job = _job(status="processing")
    evaluation = _evaluation(sync_status="syncing")
    attempt = _attempt()
    db.scalar.side_effect = [job, evaluation, attempt]

    _finalize_sync_failure(
        db,
        job_id=JOB_ID,
        worker_id="worker-test",
        error=ActuarSyncServiceError("external_unavailable", "Actuar fora do ar.", retryable=True),
        provider=None,
    )

    assert job.status == "failed"
    assert job.retry_count == 1
    assert job.next_retry_at is not None
    assert evaluation.actuar_sync_status == "sync_failed"
    assert evaluation.sync_last_error_code == "external_unavailable"


def test_build_provider_uses_csv_export_without_actuar_credentials():
    gym = SimpleNamespace(
        actuar_base_url=None,
        actuar_username=None,
        actuar_password_encrypted=None,
    )

    provider = _build_provider(
        gym=gym,
        sync_mode="csv_export",
        worker_id="worker-test",
        evidence_dir="data/test-evidence",
    )

    assert provider.__class__.__name__ == "ActuarCsvExportProvider"


def test_finalize_structural_failure_marks_manual_sync_required():
    db = MagicMock()
    job = _job(status="processing")
    evaluation = _evaluation(sync_status="syncing")
    attempt = _attempt()
    db.scalar.side_effect = [job, evaluation, attempt]

    _finalize_sync_failure(
        db,
        job_id=JOB_ID,
        worker_id="worker-test",
        error=ActuarSyncServiceError(
            "critical_fields_missing",
            "Campos criticos ausentes.",
            retryable=False,
            manual_fallback=True,
        ),
        provider=None,
    )

    assert job.status == "needs_review"
    assert evaluation.actuar_sync_status == "manual_sync_required"
    assert evaluation.sync_last_error_code == "critical_fields_missing"


def test_worker_claim_skips_local_bridge_jobs():
    db = MagicMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = None
    db.scalar.return_value = None

    job = claim_next_actuar_sync_job(db, worker_id="worker:test")

    assert job is None


def test_manual_sync_summary_lists_critical_fields():
    summary = build_manual_sync_summary(_member(), _evaluation())

    assert summary["critical_fields"]
    assert "Aluno: Aluno Sync" in summary["summary_text"]
    assert "weight" in summary["summary_text"]
    assert "height_cm" in summary["summary_text"]
    assert "body_fat_percent" in summary["summary_text"]


def test_build_actuar_field_mapping_derives_height_from_weight_and_bmi():
    mapping = build_actuar_field_mapping(_member(), _evaluation())

    critical_fields = {item["field"]: item for item in mapping["critical_fields"]}
    assert critical_fields["height_cm"]["value"] == 180
    assert critical_fields["height_cm"]["actuar_field"] == "height_cm"


def test_confirm_manual_actuar_sync_marks_evaluation_as_ready():
    db = MagicMock()
    evaluation = _evaluation(sync_status="manual_sync_required")
    current_job = _job(status="needs_review")

    with patch(
        "app.services.body_composition_actuar_sync_service.get_body_composition_evaluation_or_404",
        return_value=evaluation,
    ), patch(
        "app.services.body_composition_actuar_sync_service._get_current_sync_job",
        return_value=current_job,
    ):
        result = confirm_manual_actuar_sync(
            db,
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
            confirmed_by_user_id=uuid.UUID("77777777-7777-7777-7777-777777777777"),
            reason="Lancado manualmente no Actuar",
            note="Operacao concluida pelo professor",
    )

    assert result is evaluation
    assert evaluation.actuar_sync_status == "synced_to_actuar"
    assert current_job.status == "synced"
    assert current_job.synced_at is not None
    assert db.add.call_count >= 1


def test_get_sync_status_exposes_unsupported_fields_for_ui_transparency():
    db = MagicMock()
    evaluation = _evaluation(sync_status="manual_sync_required")
    member = _member()
    mapping = {
        "critical_fields": [{"field": "weight_kg", "actuar_field": "weight", "classification": "critical", "supported": True, "value": 84.5}],
        "non_critical_fields": [
            {"field": "bmr_kcal", "actuar_field": "bmr_kcal", "classification": "unsupported", "supported": False, "value": 1880},
            {"field": "visceral_fat", "actuar_field": "visceral_fat", "classification": "unsupported", "supported": False, "value": 9},
            {"field": "body_water_percent", "actuar_field": "body_water_percent", "classification": "optional", "supported": True, "value": 51.0},
        ],
    }

    with patch(
        "app.services.body_composition_actuar_sync_service.get_body_composition_evaluation_or_404",
        return_value=evaluation,
    ), patch(
        "app.services.body_composition_actuar_sync_service.get_member_or_404",
        return_value=member,
    ), patch(
        "app.services.body_composition_actuar_sync_service._get_current_sync_job",
        return_value=None,
    ), patch(
        "app.services.body_composition_actuar_sync_service.build_actuar_field_mapping",
        return_value=mapping,
    ), patch(
        "app.services.body_composition_actuar_sync_service.build_manual_sync_summary",
        return_value={
            "evaluation_id": EVALUATION_ID,
            "member_id": MEMBER_ID,
            "sync_status": "manual_sync_required",
            "training_ready": False,
            "critical_fields": [],
            "summary_text": "manual",
        },
    ), patch(
        "app.services.body_composition_actuar_sync_service.get_actuar_member_link",
        return_value=None,
    ):
        status = get_body_composition_sync_status(
            db,
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
        )

    assert len(status.unsupported_fields) == 2
    assert {field.field for field in status.unsupported_fields} == {"bmr_kcal", "visceral_fat"}
