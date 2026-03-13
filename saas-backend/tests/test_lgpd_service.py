"""Tests for lgpd_service covering export and anonymization."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.enums import MemberStatus, RiskLevel

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _mock_member(**overrides):
    defaults = dict(
        id=MEMBER_ID,
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


class TestAnonymizeMember:
    def test_anonymizes_all_pii(self):
        member = _mock_member()
        db = MagicMock()
        db.scalar.return_value = member
        db.refresh = MagicMock()

        from app.services.lgpd_service import anonymize_member
        result = anonymize_member(db, MEMBER_ID)

        assert result.full_name.startswith("anon-")
        assert result.email is None
        assert result.phone is None
        assert result.cpf_encrypted is None
        assert result.status == MemberStatus.CANCELLED
        assert result.deleted_at is not None
        assert "anonymized_at" in result.extra_data
        db.commit.assert_called_once()

    def test_member_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.services.lgpd_service import anonymize_member
        with pytest.raises(HTTPException) as exc_info:
            anonymize_member(db, MEMBER_ID)
        assert exc_info.value.status_code == 404


class TestExportMemberPdf:
    def test_generates_pdf(self):
        member = _mock_member()
        db = MagicMock()
        db.scalar.return_value = member

        checkin_scalars = MagicMock()
        checkin_scalars.all.return_value = []
        nps_scalars = MagicMock()
        nps_scalars.all.return_value = []
        tasks_scalars = MagicMock()
        tasks_scalars.all.return_value = []
        alerts_scalars = MagicMock()
        alerts_scalars.all.return_value = []
        audit_scalars = MagicMock()
        audit_scalars.all.return_value = []
        db.scalars.side_effect = [checkin_scalars, nps_scalars, tasks_scalars, alerts_scalars, audit_scalars]

        from app.services.lgpd_service import export_member_pdf
        buffer, filename = export_member_pdf(db, MEMBER_ID)

        assert buffer.read(4) == b"%PDF"
        assert str(MEMBER_ID) in filename

    def test_member_not_found_raises(self):
        db = MagicMock()
        db.scalar.return_value = None

        from app.services.lgpd_service import export_member_pdf
        with pytest.raises(HTTPException) as exc_info:
            export_member_pdf(db, MEMBER_ID)
        assert exc_info.value.status_code == 404
