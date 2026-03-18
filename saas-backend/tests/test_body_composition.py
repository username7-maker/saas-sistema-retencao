"""Tests for body composition services and contracts."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVALUATION_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
ATTEMPT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _ai_payload() -> dict:
    return {
        "coach_summary": "Resumo para professor.",
        "member_friendly_summary": "Resumo amigavel.",
        "risk_flags": ["percentual de gordura acima da faixa"],
        "training_focus": {
            "primary_goal": "reducao_de_gordura",
            "secondary_goal": "preservacao_de_massa_magra",
            "suggested_focuses": ["monitorar composicao corporal"],
            "cautions": ["apoio ao professor"],
        },
        "generated_at": "2026-03-17T12:00:00+00:00",
    }


class TestCreateBodyComposition:
    @patch("app.services.body_composition_service.prepare_body_composition_sync_attempt")
    @patch("app.services.body_composition_service.generate_body_composition_ai")
    @patch("app.services.body_composition_service.get_member_or_404")
    def test_creates_with_ocr_metadata_and_pending_sync(self, mock_get_member, mock_generate_ai, mock_prepare_sync):
        member = SimpleNamespace(id=MEMBER_ID, full_name="Aluno")
        mock_get_member.return_value = member
        mock_generate_ai.return_value = _ai_payload()

        def _prepare(db, *, member, evaluation, force_retry=False):
            evaluation.actuar_sync_status = "pending"
            evaluation.actuar_sync_mode = "csv_export"
            return SimpleNamespace(id=ATTEMPT_ID, status="pending")

        mock_prepare_sync.side_effect = _prepare
        db = MagicMock()

        from app.schemas.body_composition import BodyCompositionEvaluationCreate
        payload = BodyCompositionEvaluationCreate(
            evaluation_date=date(2026, 3, 1),
            source="ocr_receipt",
            weight_kg=84.5,
            body_fat_kg=19.46,
            body_fat_percent=23.0,
            fat_free_mass_kg=65.0,
            health_score=62,
            raw_ocr_text="Body composition",
            ocr_confidence=0.88,
            ocr_warnings_json=[{"field": "body_fat_percent", "message": "Revisar", "severity": "warning"}],
            needs_review=True,
            reviewed_manually=False,
            device_profile="tezewa_receipt_v1",
            device_model="Tezewa",
            parsed_from_image=True,
            ocr_source_file_ref="local://receipt.jpg",
            measured_ranges_json={"body_fat_percent": {"min": 11.0, "max": 21.0}},
        )

        from app.services.body_composition_service import create_body_composition_evaluation

        evaluation, attempt = create_body_composition_evaluation(db, GYM_ID, MEMBER_ID, payload)

        assert evaluation.gym_id == GYM_ID
        assert evaluation.member_id == MEMBER_ID
        assert evaluation.source == "ocr_receipt"
        assert evaluation.reviewed_manually is False
        assert evaluation.device_profile == "tezewa_receipt_v1"
        assert evaluation.fat_free_mass_kg == 65.0
        assert evaluation.lean_mass_kg is None
        assert evaluation.actuar_sync_status == "pending"
        assert evaluation.ai_coach_summary == "Resumo para professor."
        assert attempt.id == ATTEMPT_ID
        db.add.assert_called_once()
        assert db.flush.call_count == 2

    @patch("app.services.body_composition_service.prepare_body_composition_sync_attempt", return_value=None)
    @patch("app.services.body_composition_service.generate_body_composition_ai")
    @patch("app.services.body_composition_service.get_member_or_404")
    def test_manual_source_marks_reviewed_manually_true(self, mock_get_member, mock_generate_ai, mock_prepare_sync):
        mock_get_member.return_value = SimpleNamespace(id=MEMBER_ID)
        mock_generate_ai.return_value = _ai_payload()
        db = MagicMock()

        from app.schemas.body_composition import BodyCompositionEvaluationCreate
        from app.services.body_composition_service import create_body_composition_evaluation

        evaluation, attempt = create_body_composition_evaluation(
            db,
            GYM_ID,
            MEMBER_ID,
            BodyCompositionEvaluationCreate(
                evaluation_date=date(2026, 3, 2),
                source="manual",
                weight_kg=80.0,
            ),
        )

        assert evaluation.reviewed_manually is True
        assert attempt is None


class TestUpdateBodyComposition:
    @patch("app.services.body_composition_service.prepare_body_composition_sync_attempt")
    @patch("app.services.body_composition_service.generate_body_composition_ai")
    @patch("app.services.body_composition_service.get_body_composition_evaluation_or_404")
    @patch("app.services.body_composition_service.get_member_or_404")
    def test_updates_existing_evaluation(self, mock_get_member, mock_get_evaluation, mock_generate_ai, mock_prepare_sync):
        member = SimpleNamespace(id=MEMBER_ID, full_name="Aluno")
        evaluation = SimpleNamespace(
            id=EVALUATION_ID,
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            source="manual",
            reviewed_manually=True,
            ai_coach_summary=None,
            ai_member_friendly_summary=None,
            ai_risk_flags_json=None,
            ai_training_focus_json=None,
            ai_generated_at=None,
        )
        mock_get_member.return_value = member
        mock_get_evaluation.return_value = evaluation
        mock_generate_ai.return_value = _ai_payload()
        mock_prepare_sync.return_value = None
        db = MagicMock()

        from app.schemas.body_composition import BodyCompositionEvaluationUpdate
        from app.services.body_composition_service import update_body_composition_evaluation

        updated, attempt = update_body_composition_evaluation(
            db,
            GYM_ID,
            MEMBER_ID,
            EVALUATION_ID,
            BodyCompositionEvaluationUpdate(
                evaluation_date=date(2026, 3, 3),
                source="manual",
                weight_kg=82.0,
                fat_free_mass_kg=63.2,
                lean_mass_kg=61.0,
                reviewed_manually=True,
            ),
        )

        assert updated.weight_kg == 82.0
        assert updated.fat_free_mass_kg == 63.2
        assert updated.lean_mass_kg == 61.0
        assert updated.reviewed_manually is True
        assert updated.ai_training_focus_json["primary_goal"] == "reducao_de_gordura"
        assert attempt is None
        db.flush.assert_called_once()


class TestListBodyComposition:
    def test_lists(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.body_composition_service import list_body_composition_evaluations

        result = list_body_composition_evaluations(db, GYM_ID, MEMBER_ID)
        assert result == []


class TestSyncLookup:
    def test_get_body_composition_evaluation_or_404_respects_member_and_gym_scope(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.services.body_composition_actuar_sync_service import get_body_composition_evaluation_or_404

        try:
            get_body_composition_evaluation_or_404(
                db,
                gym_id=GYM_ID,
                member_id=MEMBER_ID,
                evaluation_id=EVALUATION_ID,
            )
        except HTTPException as exc:
            assert exc.status_code == 404
            assert "Bioimpedancia" in exc.detail
        else:
            raise AssertionError("Expected HTTPException for cross-tenant or missing evaluation")
