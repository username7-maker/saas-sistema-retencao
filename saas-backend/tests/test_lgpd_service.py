"""Tests for lgpd_service covering export and anonymization."""

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.enums import MemberStatus, RiskLevel

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _mock_member(**overrides):
    defaults = dict(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Maria Teste",
        email="maria@test.com",
        phone="11999887766",
        cpf_encrypted="encrypted-cpf",
        plan_name="Gold",
        monthly_fee=Decimal("99.90"),
        status=MemberStatus.ACTIVE,
        risk_score=20,
        risk_level=RiskLevel.YELLOW,
        extra_data={},
        deleted_at=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _scalars_result(items):
    mocked = MagicMock()
    mocked.all.return_value = items
    return mocked


class TestAnonymizeMember:
    def test_anonymizes_member_and_related_records(self):
        member = _mock_member()
        converted_lead = SimpleNamespace(
            full_name="Lead Original",
            email="lead@test.com",
            phone="5511999990001",
            notes=["private note"],
            lost_reason="valor alto",
        )
        message_log = SimpleNamespace(
            recipient="5511999990001",
            content="Mensagem sensivel",
            error_detail="timeout with phone 5511999990001",
            extra_data={"instance_source": "gym", "response_status": 200},
        )
        evaluation = SimpleNamespace(
            notes="nota clinica",
            report_file_url="https://files/report.pdf",
            raw_ocr_text="texto bruto OCR",
            ocr_source_file_ref="s3://ocr/ref",
            ai_coach_summary="coach summary",
            ai_member_friendly_summary="member summary",
            actuar_external_id="actuar-123",
            actuar_last_error="erro com nome do aluno",
            sync_last_error_message="erro detalhado",
            data_quality_flags_json=["missing_body_fat_percent"],
        )
        nps = SimpleNamespace(comment="comentario sensivel", sentiment_summary="resumo", extra_data={"channel": "whatsapp"})
        constraints = SimpleNamespace(
            medical_conditions="asma",
            injuries="joelho",
            medications="anti-inflamatorio",
            contraindications="saltos",
            notes="nao expor",
            restrictions={"injury": True},
        )
        db = MagicMock()
        db.scalar.side_effect = [member, constraints]
        db.scalars.side_effect = [
            _scalars_result([converted_lead]),
            _scalars_result([message_log]),
            _scalars_result([evaluation]),
            _scalars_result([nps]),
        ]

        from app.services.lgpd_service import anonymize_member

        result = anonymize_member(db, MEMBER_ID, GYM_ID)

        assert result.full_name.startswith("anon-")
        assert result.email is None
        assert result.phone is None
        assert result.cpf_encrypted is None
        assert result.status == MemberStatus.CANCELLED
        assert result.deleted_at is not None
        assert "anonymized_at" in result.extra_data
        assert converted_lead.full_name.endswith("-lead")
        assert converted_lead.email is None
        assert converted_lead.phone is None
        assert converted_lead.notes == []
        assert converted_lead.lost_reason is None
        assert message_log.recipient.endswith("-message")
        assert message_log.content == "[redacted-by-lgpd]"
        assert message_log.error_detail == "[redacted-by-lgpd]"
        assert message_log.extra_data["redacted"] is True
        assert evaluation.notes is None
        assert evaluation.raw_ocr_text is None
        assert evaluation.ai_coach_summary is None
        assert evaluation.actuar_external_id is None
        assert "lgpd_redacted" in evaluation.data_quality_flags_json
        assert nps.comment is None
        assert nps.sentiment_summary is None
        assert nps.extra_data["redacted"] is True
        assert constraints.medical_conditions is None
        assert constraints.injuries is None
        assert constraints.notes is None
        assert constraints.restrictions["redacted"] is True

    def test_member_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.services.lgpd_service import anonymize_member

        with pytest.raises(HTTPException) as exc_info:
            anonymize_member(db, MEMBER_ID, GYM_ID)
        assert exc_info.value.status_code == 404


class TestExportMemberPdf:
    def test_generates_pdf(self):
        member = _mock_member()
        db = MagicMock()
        db.scalar.side_effect = [member, None, None]
        db.scalars.side_effect = [
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([]),
        ]

        from app.services.lgpd_service import export_member_pdf

        buffer, filename = export_member_pdf(db, MEMBER_ID, GYM_ID)

        assert buffer.read(4) == b"%PDF"
        assert str(MEMBER_ID) in filename

    def test_member_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.services.lgpd_service import export_member_pdf

        with pytest.raises(HTTPException) as exc_info:
            export_member_pdf(db, MEMBER_ID, GYM_ID)
        assert exc_info.value.status_code == 404
