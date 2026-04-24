"""Tests for body composition services and contracts."""

import uuid
from datetime import UTC, date, datetime
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
            evaluation.actuar_sync_status = "sync_pending"
            evaluation.actuar_sync_mode = "assisted_rpa"
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
        assert evaluation.lean_mass_kg == 65.0
        assert evaluation.actuar_sync_status == "sync_pending"
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

    @patch("app.services.body_composition_service.get_member_or_404")
    def test_rejects_empty_evaluation_without_any_metric(self, mock_get_member):
        mock_get_member.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()

        from app.schemas.body_composition import BodyCompositionEvaluationCreate
        from app.services.body_composition_service import create_body_composition_evaluation

        try:
            create_body_composition_evaluation(
                db,
                GYM_ID,
                MEMBER_ID,
                BodyCompositionEvaluationCreate(
                    evaluation_date=date(2026, 4, 9),
                    source="manual",
                ),
            )
        except HTTPException as exc:
            assert exc.status_code == 422
            assert "ao menos uma metrica" in str(exc.detail).lower()
        else:
            raise AssertionError("Expected HTTPException for empty body composition evaluation")


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

    @patch("app.services.body_composition_service.get_body_composition_evaluation_or_404")
    @patch("app.services.body_composition_service.get_member_or_404")
    def test_rejects_update_that_clears_all_metrics(self, mock_get_member, mock_get_evaluation):
        mock_get_member.return_value = SimpleNamespace(id=MEMBER_ID, full_name="Aluno")
        mock_get_evaluation.return_value = SimpleNamespace(id=EVALUATION_ID, gym_id=GYM_ID, member_id=MEMBER_ID)
        db = MagicMock()

        from app.schemas.body_composition import BodyCompositionEvaluationUpdate
        from app.services.body_composition_service import update_body_composition_evaluation

        try:
            update_body_composition_evaluation(
                db,
                GYM_ID,
                MEMBER_ID,
                EVALUATION_ID,
                BodyCompositionEvaluationUpdate(
                    evaluation_date=date(2026, 4, 9),
                    source="manual",
                ),
            )
        except HTTPException as exc:
            assert exc.status_code == 422
            assert "ao menos uma metrica" in str(exc.detail).lower()
        else:
            raise AssertionError("Expected HTTPException when update payload removes all measurements")


class TestListBodyComposition:
    def test_lists(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars

        from app.services.body_composition_service import list_body_composition_evaluations

        result = list_body_composition_evaluations(db, GYM_ID, MEMBER_ID)
        assert result == []


class TestBodyCompositionDelivery:
    @patch("app.services.body_composition_delivery_service.send_whatsapp_document_sync")
    @patch("app.services.body_composition_delivery_service.generate_body_composition_pdf")
    @patch("app.services.body_composition_delivery_service.get_gym_instance", return_value="gym_instance")
    @patch("app.services.body_composition_delivery_service.get_body_composition_evaluation_or_404")
    @patch("app.services.body_composition_delivery_service.get_member_or_404")
    def test_send_whatsapp_summary_uses_member_phone(
        self,
        mock_get_member,
        mock_get_evaluation,
        mock_get_instance,
        mock_generate_pdf,
        mock_send_document,
    ):
        member = SimpleNamespace(id=MEMBER_ID, full_name="Erick Bedin", phone="11999999999")
        evaluation = SimpleNamespace(
            id=EVALUATION_ID,
            evaluation_date=date(2026, 3, 30),
            ai_member_friendly_summary="Seu exame mostra um bom ponto de partida para organizar o acompanhamento.",
            ai_risk_flags_json=["Peso acima da faixa recomendada"],
            ai_training_focus_json={"primary_goal": "reducao_de_gordura"},
            weight_kg=84.5,
            body_fat_percent=23.0,
            muscle_mass_kg=37.2,
            skeletal_muscle_kg=35.6,
            waist_hip_ratio=0.88,
            visceral_fat_level=9.1,
            bmi=26.7,
            health_score=62,
        )
        mock_get_member.return_value = member
        mock_get_evaluation.return_value = evaluation
        mock_generate_pdf.return_value = (b"%PDF-1.4 fake", "bioimpedancia_erick.pdf")
        mock_send_document.return_value = SimpleNamespace(
            id=uuid.uuid4(),
            status="sent",
            recipient="5511999999999",
            error_detail=None,
            extra_data={"file_name": "bioimpedancia_erick.pdf"},
        )
        db = MagicMock()

        from app.services.body_composition_delivery_service import send_body_composition_whatsapp_summary

        log = send_body_composition_whatsapp_summary(
            db,
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
        )

        assert log.status == "sent"
        assert mock_send_document.call_args.kwargs["phone"] == "11999999999"
        assert mock_send_document.call_args.kwargs["instance"] == "gym_instance"

    @patch("app.services.body_composition_delivery_service.render_premium_report_pdf", return_value=b"%PDF-1.4 premium")
    def test_generate_body_composition_pdf_contains_core_sections(self, _mock_render_pdf):
        member = SimpleNamespace(full_name="Erick Bedin")
        evaluation = SimpleNamespace(
            evaluation_date=date(2026, 3, 30),
            id=EVALUATION_ID,
            gym=None,
            ai_member_friendly_summary="Seu exame mostra um bom ponto de partida para organizar os proximos passos.",
            ai_coach_summary="Leitura tecnica resumida.",
            ai_risk_flags_json=["Peso acima da faixa recomendada", "Gordura visceral elevada"],
            ai_training_focus_json={
                "primary_goal": "reducao_de_gordura",
                "secondary_goal": "preservacao_de_massa_magra",
                "suggested_focuses": ["reduzir gordura corporal"],
            },
            weight_kg=84.5,
            body_fat_percent=23.0,
            muscle_mass_kg=37.2,
            skeletal_muscle_kg=35.6,
            waist_hip_ratio=0.88,
            visceral_fat_level=9.1,
            bmi=26.7,
            health_score=62,
        )

        from app.services.body_composition_delivery_service import generate_body_composition_pdf

        pdf_bytes, filename = generate_body_composition_pdf(member, evaluation)

        assert filename.endswith(".pdf")
        assert pdf_bytes.startswith(b"%PDF")

    @patch("app.services.body_composition_delivery_service.render_premium_report_pdf", return_value=b"%PDF-1.4 premium-tech")
    def test_generate_body_composition_technical_pdf_uses_technical_filename(self, _mock_render_pdf):
        member = SimpleNamespace(full_name="Erick Bedin")
        evaluation = SimpleNamespace(
            evaluation_date=date(2026, 3, 30),
            id=EVALUATION_ID,
            gym=None,
            ai_member_friendly_summary="Resumo do aluno.",
            ai_coach_summary="Leitura tecnica resumida.",
            ai_risk_flags_json=["Peso acima da faixa recomendada"],
            ai_training_focus_json={"primary_goal": "reducao_de_gordura", "secondary_goal": "preservacao_de_massa_magra"},
            weight_kg=84.5,
            body_fat_percent=23.0,
            muscle_mass_kg=37.2,
            skeletal_muscle_kg=35.6,
            waist_hip_ratio=0.88,
            visceral_fat_level=9.1,
            bmi=26.7,
            health_score=62,
        )

        from app.services.body_composition_delivery_service import generate_body_composition_technical_pdf

        pdf_bytes, filename = generate_body_composition_technical_pdf(member, evaluation)

        assert filename.startswith("bioimpedancia_tecnica_")
        assert pdf_bytes.startswith(b"%PDF")


class TestBodyCompositionPremiumReportDomain:
    def test_resolve_persistence_fields_generates_quality_flags_and_reviewer(self):
        from app.services.body_composition_report_service import resolve_body_composition_persistence_fields

        reviewer_user_id = uuid.uuid4()
        payload = resolve_body_composition_persistence_fields(
            {
                "evaluation_date": date(2026, 4, 14),
                "reviewed_manually": True,
                "needs_review": False,
                "ocr_confidence": 0.61,
                "bmi": 82.0,
                "body_fat_percent": None,
                "muscle_mass_kg": None,
            },
            reviewer_user_id=reviewer_user_id,
        )

        assert payload["measured_at"].date() == date(2026, 4, 14)
        assert payload["reviewer_user_id"] == reviewer_user_id
        assert "missing_body_fat_percent" in payload["data_quality_flags_json"]
        assert "missing_muscle_mass" in payload["data_quality_flags_json"]
        assert "suspect_bmi" in payload["data_quality_flags_json"]
        assert "ocr_low_confidence" in payload["data_quality_flags_json"]

    def test_resolve_persistence_fields_mirrors_fat_free_and_lean_mass_for_legacy_compatibility(self):
        from app.services.body_composition_report_service import resolve_body_composition_persistence_fields

        payload = resolve_body_composition_persistence_fields(
            {
                "evaluation_date": date(2026, 4, 14),
                "reviewed_manually": True,
                "fat_free_mass_kg": 65.1,
                "lean_mass_kg": None,
            },
            reviewer_user_id=uuid.uuid4(),
        )

        assert payload["fat_free_mass_kg"] == 65.1
        assert payload["lean_mass_kg"] == 65.1

    def test_generate_body_composition_insights_detects_fat_loss_with_muscle_stability(self):
        from app.services.body_composition_report_service import generate_body_composition_insights

        previous = SimpleNamespace(
            id=uuid.uuid4(),
            evaluation_date=date(2026, 3, 10),
            measured_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            body_fat_percent=25.0,
            muscle_mass_kg=35.2,
            weight_kg=85.4,
            visceral_fat_level=10.0,
            bmi=27.0,
            basal_metabolic_rate_kcal=1860,
        )
        current = SimpleNamespace(
            id=uuid.uuid4(),
            evaluation_date=date(2026, 4, 14),
            measured_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            body_fat_percent=23.0,
            muscle_mass_kg=35.6,
            weight_kg=84.5,
            visceral_fat_level=9.0,
            bmi=26.7,
            basal_metabolic_rate_kcal=1880,
        )

        insights = generate_body_composition_insights(current, [previous, current])

        assert any(insight.key == "fat_down_muscle_stable" for insight in insights)
        assert any(any("% gordura variou" in reason for reason in insight.reasons) for insight in insights)

    def test_build_report_payload_exposes_history_and_comparison(self):
        member = SimpleNamespace(
            id=MEMBER_ID,
            full_name="Erick Bedin",
            birthdate=date(2004, 4, 9),
            gym=SimpleNamespace(name="AI GYM OS Piloto"),
            assigned_user=SimpleNamespace(full_name="Automicai Owner"),
        )
        previous = SimpleNamespace(
            id=uuid.uuid4(),
            evaluation_date=date(2026, 3, 10),
            measured_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            weight_kg=85.7,
            body_fat_percent=24.8,
            body_fat_kg=20.2,
            muscle_mass_kg=35.1,
            skeletal_muscle_kg=34.7,
            visceral_fat_level=10.0,
            bmi=27.1,
            basal_metabolic_rate_kcal=1848,
            notes=None,
            reviewed_manually=True,
            parsing_confidence=0.92,
            data_quality_flags_json=[],
        )
        current = SimpleNamespace(
            id=EVALUATION_ID,
            evaluation_date=date(2026, 4, 14),
            measured_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            age_years=21,
            sex="male",
            height_cm=178.0,
            weight_kg=84.5,
            body_fat_percent=23.0,
            body_fat_kg=19.4,
            body_water_kg=43.3,
            protein_kg=17.7,
            inorganic_salt_kg=3.2,
            fat_free_mass_kg=65.1,
            muscle_mass_kg=35.6,
            skeletal_muscle_kg=35.0,
            visceral_fat_level=9.0,
            waist_hip_ratio=0.88,
            health_score=62,
            physical_age=26,
            bmi=26.7,
            basal_metabolic_rate_kcal=1880,
            target_weight_kg=78.0,
            weight_control_kg=-6.5,
            fat_control_kg=-5.2,
            muscle_control_kg=0.8,
            total_energy_kcal=3008,
            notes="Manter treino de forca.",
            reviewed_manually=True,
            parsing_confidence=0.93,
            data_quality_flags_json=[],
        )

        from app.services.body_composition_delivery_service import build_body_composition_report_payload

        payload = build_body_composition_report_payload(member, current, history=[previous, current])

        assert payload.header.member_name == "Erick Bedin"
        assert payload.previous_evaluation_id == previous.id
        assert len(payload.primary_cards) == 6
        assert len(payload.history_series) == 4
        assert any(row.key == "weight_kg" for row in payload.comparison_rows)
        assert payload.methodological_note


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


class TestBodyCompositionPdfRoutes:
    @patch("app.routers.members.log_audit_event")
    @patch("app.routers.members.get_request_context", return_value={"ip_address": "127.0.0.1", "user_agent": "pytest"})
    @patch("app.routers.members.generate_body_composition_pdf", return_value=(b"%PDF-1.4 summary", "bioimpedancia_erick.pdf"))
    @patch("app.routers.members.get_body_composition_evaluation_or_404")
    @patch("app.routers.members.get_member_or_404")
    def test_export_body_composition_pdf_endpoint_returns_pdf(
        self,
        mock_get_member,
        mock_get_evaluation,
        _mock_generate_pdf,
        _mock_context,
        _mock_audit,
    ):
        member = SimpleNamespace(id=MEMBER_ID, full_name="Erick Bedin")
        evaluation = SimpleNamespace(id=EVALUATION_ID)
        mock_get_member.return_value = member
        mock_get_evaluation.return_value = evaluation
        db = MagicMock()
        db.scalar.return_value = None

        from app.routers.members import export_body_composition_pdf_endpoint

        response = export_body_composition_pdf_endpoint(
            request=MagicMock(),
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
            db=db,
            current_user=SimpleNamespace(gym_id=GYM_ID, full_name="Owner"),
        )

        assert response.media_type == "application/pdf"
        assert response.body.startswith(b"%PDF")
        db.commit.assert_called_once()


class TestBodyCompositionReportRoute:
    @patch("app.routers.members.list_body_composition_evaluations")
    @patch("app.routers.members.get_body_composition_evaluation_or_404")
    @patch("app.routers.members.get_member_or_404")
    def test_report_endpoint_returns_semantic_payload(
        self,
        mock_get_member,
        mock_get_evaluation,
        mock_list_history,
    ):
        member = SimpleNamespace(
            id=MEMBER_ID,
            full_name="Erick Bedin",
            birthdate=date(2004, 4, 9),
            gym=SimpleNamespace(name="AI GYM OS Piloto"),
            assigned_user=SimpleNamespace(full_name="Automicai Owner"),
        )
        previous = SimpleNamespace(
            id=uuid.uuid4(),
            evaluation_date=date(2026, 3, 10),
            measured_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            weight_kg=85.7,
            body_fat_percent=24.8,
            muscle_mass_kg=35.1,
            visceral_fat_level=10.0,
            bmi=27.1,
            basal_metabolic_rate_kcal=1848,
        )
        current = SimpleNamespace(
            id=EVALUATION_ID,
            evaluation_date=date(2026, 4, 14),
            measured_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            age_years=21,
            sex="male",
            height_cm=178.0,
            weight_kg=84.5,
            body_fat_percent=23.0,
            body_fat_kg=19.4,
            muscle_mass_kg=35.6,
            skeletal_muscle_kg=35.0,
            visceral_fat_level=9.0,
            waist_hip_ratio=0.88,
            bmi=26.7,
            basal_metabolic_rate_kcal=1880,
            reviewed_manually=True,
            parsing_confidence=0.93,
            data_quality_flags_json=[],
            notes=None,
        )
        mock_get_member.return_value = member
        mock_get_evaluation.return_value = current
        mock_list_history.return_value = [previous, current]
        db = MagicMock()

        from app.routers.members import get_body_composition_report_endpoint

        payload = get_body_composition_report_endpoint(
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
            db=db,
            current_user=SimpleNamespace(gym_id=GYM_ID),
        )

        assert payload.current_evaluation_id == EVALUATION_ID
        assert payload.header.member_name == "Erick Bedin"
        assert payload.previous_evaluation_id == previous.id
        assert any(card.key == "weight_kg" for card in payload.primary_cards)

    @patch("app.routers.members.log_audit_event")
    @patch("app.routers.members.get_request_context", return_value={"ip_address": "127.0.0.1", "user_agent": "pytest"})
    @patch("app.routers.members.generate_body_composition_technical_pdf", return_value=(b"%PDF-1.4 technical", "bioimpedancia_tecnica_erick.pdf"))
    @patch("app.routers.members.get_body_composition_evaluation_or_404")
    @patch("app.routers.members.get_member_or_404")
    def test_export_body_composition_technical_pdf_endpoint_returns_pdf(
        self,
        mock_get_member,
        mock_get_evaluation,
        _mock_generate_pdf,
        _mock_context,
        _mock_audit,
    ):
        member = SimpleNamespace(id=MEMBER_ID, full_name="Erick Bedin")
        evaluation = SimpleNamespace(id=EVALUATION_ID)
        mock_get_member.return_value = member
        mock_get_evaluation.return_value = evaluation
        db = MagicMock()
        db.scalar.return_value = None

        from app.routers.members import export_body_composition_technical_pdf_endpoint

        response = export_body_composition_technical_pdf_endpoint(
            request=MagicMock(),
            member_id=MEMBER_ID,
            evaluation_id=EVALUATION_ID,
            db=db,
            current_user=SimpleNamespace(gym_id=GYM_ID, full_name="Owner"),
        )

        assert response.media_type == "application/pdf"
        assert response.body.startswith(b"%PDF")
        db.commit.assert_called_once()
