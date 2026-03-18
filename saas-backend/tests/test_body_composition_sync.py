"""Tests for body composition Actuar sync flow."""

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.integrations.actuar.base import ActuarSyncOutcome


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVALUATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
ATTEMPT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _member():
    return SimpleNamespace(id=MEMBER_ID, extra_data={}, full_name="Aluno")


def _evaluation(sync_status: str = "pending"):
    return SimpleNamespace(
        id=EVALUATION_ID,
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        evaluation_date=date(2026, 3, 17),
        weight_kg=84.5,
        body_fat_percent=23.0,
        body_fat_kg=19.46,
        bmi=26.7,
        visceral_fat_level=9.1,
        skeletal_muscle_kg=35.6,
        basal_metabolic_rate_kcal=1880,
        health_score=62,
        notes="Observacoes",
        source="ocr_receipt",
        device_profile="tezewa_receipt_v1",
        device_model="Tezewa",
        actuar_sync_status=sync_status,
        actuar_sync_mode="csv_export",
        actuar_external_id=None,
        actuar_last_synced_at=None,
        actuar_last_error=None,
    )


def _attempt(status: str = "pending", payload_snapshot_json=None):
    return SimpleNamespace(
        id=ATTEMPT_ID,
        gym_id=GYM_ID,
        body_composition_evaluation_id=EVALUATION_ID,
        sync_mode="csv_export",
        provider="actuar_csv_export",
        status=status,
        error=None,
        payload_snapshot_json=payload_snapshot_json or {"evaluation_id": str(EVALUATION_ID)},
        created_at=datetime(2026, 3, 17, tzinfo=timezone.utc),
    )


class TestPrepareSyncAttempt:
    def test_disabled_mode_keeps_local_save_and_returns_none(self):
        db = MagicMock()
        member = _member()
        evaluation = _evaluation(sync_status="disabled")

        with patch("app.services.body_composition_actuar_sync_service.settings.actuar_enabled", False):
            from app.services.body_composition_actuar_sync_service import prepare_body_composition_sync_attempt

            attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation)

        assert attempt is None
        assert evaluation.actuar_sync_status == "disabled"
        assert evaluation.actuar_sync_mode == "disabled"

    def test_enabled_mode_creates_pending_attempt_with_payload_snapshot(self):
        db = MagicMock()
        member = _member()
        evaluation = _evaluation(sync_status="disabled")

        with patch("app.services.body_composition_actuar_sync_service.settings.actuar_enabled", True), patch(
            "app.services.body_composition_actuar_sync_service.settings.actuar_sync_mode",
            "csv_export",
        ):
            from app.services.body_composition_actuar_sync_service import prepare_body_composition_sync_attempt

            attempt = prepare_body_composition_sync_attempt(db, member=member, evaluation=evaluation)

        assert attempt is not None
        assert attempt.status == "pending"
        assert attempt.payload_snapshot_json["evaluation_id"] == str(EVALUATION_ID)
        assert evaluation.actuar_sync_status == "pending"
        assert evaluation.actuar_sync_mode == "csv_export"
        db.add.assert_called_once()
        db.flush.assert_called_once()


class TestRetrySync:
    @patch("app.services.body_composition_actuar_sync_service.prepare_body_composition_sync_attempt")
    @patch("app.services.body_composition_actuar_sync_service.get_member_or_404")
    @patch("app.services.body_composition_actuar_sync_service.get_body_composition_evaluation_or_404")
    def test_failed_status_allows_retry(self, mock_get_evaluation, mock_get_member, mock_prepare):
        db = MagicMock()
        evaluation = _evaluation(sync_status="failed")
        mock_get_evaluation.return_value = evaluation
        mock_get_member.return_value = _member()
        mock_prepare.return_value = _attempt()

        from app.services.body_composition_actuar_sync_service import schedule_body_composition_sync_retry

        updated, attempt = schedule_body_composition_sync_retry(
            db,
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
        )

        assert updated is evaluation
        assert attempt.status == "pending"

    @patch("app.services.body_composition_actuar_sync_service.get_body_composition_evaluation_or_404")
    def test_terminal_status_blocks_retry(self, mock_get_evaluation):
        db = MagicMock()
        mock_get_evaluation.return_value = _evaluation(sync_status="synced")

        from app.services.body_composition_actuar_sync_service import schedule_body_composition_sync_retry

        with pytest.raises(HTTPException) as exc:
            schedule_body_composition_sync_retry(
                db,
                gym_id=GYM_ID,
                member_id=MEMBER_ID,
                evaluation_id=EVALUATION_ID,
            )
        assert exc.value.status_code == 409


class TestExecuteSyncAttempt:
    @patch("app.services.body_composition_actuar_sync_service.get_member_or_404")
    @patch("app.services.body_composition_actuar_sync_service._get_provider")
    @patch("app.services.body_composition_actuar_sync_service._claim_attempt", return_value=True)
    def test_legitimate_pending_attempt_claims_and_runs(self, mock_claim, mock_get_provider, mock_get_member):
        db = MagicMock()
        evaluation = _evaluation(sync_status="pending")
        attempt = _attempt()
        db.scalar.side_effect = [evaluation, attempt, attempt]
        mock_get_member.return_value = _member()
        provider = MagicMock()
        provider.push_body_composition.return_value = ActuarSyncOutcome(
            status="exported",
            provider="actuar_csv_export",
            external_id="csv-export:1",
            payload_snapshot_json={"evaluation_id": str(EVALUATION_ID)},
        )
        mock_get_provider.return_value = provider

        from app.services.body_composition_actuar_sync_service import _execute_body_composition_sync_attempt

        _execute_body_composition_sync_attempt(
            db,
            evaluation_id=EVALUATION_ID,
            attempt_id=ATTEMPT_ID,
            force_retry=False,
        )

        mock_claim.assert_called_once_with(db, ATTEMPT_ID)
        provider.push_body_composition.assert_called_once()
        assert attempt.status == "exported"
        assert evaluation.actuar_sync_status == "exported"
        assert evaluation.actuar_external_id == "csv-export:1"

    @patch("app.services.body_composition_actuar_sync_service._get_provider")
    @patch("app.services.body_composition_actuar_sync_service._claim_attempt", return_value=False)
    def test_duplicate_execution_aborts_when_claim_fails(self, mock_claim, mock_get_provider):
        db = MagicMock()
        evaluation = _evaluation(sync_status="pending")
        attempt = _attempt()
        db.scalar.side_effect = [evaluation, attempt]

        from app.services.body_composition_actuar_sync_service import _execute_body_composition_sync_attempt

        _execute_body_composition_sync_attempt(
            db,
            evaluation_id=EVALUATION_ID,
            attempt_id=ATTEMPT_ID,
            force_retry=False,
        )

        mock_claim.assert_called_once_with(db, ATTEMPT_ID)
        mock_get_provider.assert_not_called()

    def test_terminal_status_skips_non_forced_execution(self):
        db = MagicMock()
        evaluation = _evaluation(sync_status="synced")
        attempt = _attempt()
        db.scalar.side_effect = [evaluation, attempt]

        from app.services.body_composition_actuar_sync_service import _execute_body_composition_sync_attempt

        _execute_body_composition_sync_attempt(
            db,
            evaluation_id=EVALUATION_ID,
            attempt_id=ATTEMPT_ID,
            force_retry=False,
        )

        assert attempt.status == "skipped"
        assert attempt.error is not None

    @patch("app.services.body_composition_actuar_sync_service.get_member_or_404")
    @patch("app.services.body_composition_actuar_sync_service._get_provider")
    @patch("app.services.body_composition_actuar_sync_service._claim_attempt", return_value=True)
    def test_failed_status_allows_new_retry_attempt(self, mock_claim, mock_get_provider, mock_get_member):
        db = MagicMock()
        evaluation = _evaluation(sync_status="failed")
        attempt = _attempt()
        db.scalar.side_effect = [evaluation, attempt, attempt]
        mock_get_member.return_value = _member()
        provider = MagicMock()
        provider.push_body_composition.return_value = ActuarSyncOutcome(
            status="synced",
            provider="actuar_http_api",
            external_id="remote-123",
            payload_snapshot_json={"evaluation_id": str(EVALUATION_ID)},
        )
        mock_get_provider.return_value = provider

        from app.services.body_composition_actuar_sync_service import _execute_body_composition_sync_attempt

        _execute_body_composition_sync_attempt(
            db,
            evaluation_id=EVALUATION_ID,
            attempt_id=ATTEMPT_ID,
            force_retry=True,
        )

        assert attempt.status == "synced"
        assert evaluation.actuar_sync_status == "synced"
