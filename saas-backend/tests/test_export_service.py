"""Tests for export_service covering CSV generation."""

import csv
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.enums import CheckinSource, MemberStatus, RiskLevel
from app.services.export_service import (
    export_checkins_csv,
    export_checkins_template_csv,
    export_members_csv,
    export_members_template_csv,
)


MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _mock_member(**overrides):
    defaults = dict(
        id=MEMBER_ID,
        full_name="Joao Silva",
        email="joao@test.com",
        phone="11999998888",
        plan_name="Premium",
        monthly_fee=Decimal("129.90"),
        join_date=date(2026, 1, 15),
        status=MemberStatus.ACTIVE,
        preferred_shift="manha",
        nps_last_score=8,
        loyalty_months=6,
        risk_score=15,
        risk_level=RiskLevel.YELLOW,
        last_checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
        extra_data={"external_id": "A12345"},
        deleted_at=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _parse_csv_bytes(buffer) -> list[dict]:
    content = buffer.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(content))
    return list(reader)


class TestExportMembersCsv:
    def test_generates_csv_with_headers(self):
        member = _mock_member()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member]
        db = MagicMock()
        db.scalars.return_value = mock_scalars

        buffer, filename = export_members_csv(db)
        assert "members_export_" in filename
        assert filename.endswith(".csv")

        rows = _parse_csv_bytes(buffer)
        assert len(rows) == 1
        assert rows[0]["full_name"] == "Joao Silva"
        assert rows[0]["phone"] == "11999998888"
        assert rows[0]["risk_level"] == "yellow"

    def test_empty_member_list(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db = MagicMock()
        db.scalars.return_value = mock_scalars

        buffer, filename = export_members_csv(db)
        rows = _parse_csv_bytes(buffer)
        assert len(rows) == 0

    def test_escapes_spreadsheet_formulas(self):
        member = _mock_member(full_name="=HYPERLINK(\"http://evil.test\")")
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [member]
        db = MagicMock()
        db.scalars.return_value = mock_scalars

        buffer, _filename = export_members_csv(db)
        rows = _parse_csv_bytes(buffer)
        assert rows[0]["full_name"].startswith("'=")


class TestExportCheckinsCsv:
    def test_generates_csv_with_dates(self):
        member = _mock_member()
        checkin = SimpleNamespace(
            id=uuid.uuid4(),
            member_id=MEMBER_ID,
            checkin_at=datetime(2026, 3, 10, 18, 30, tzinfo=timezone.utc),
            source=SimpleNamespace(value="turnstile"),
            hour_bucket=18,
            weekday=1,
        )
        db = MagicMock()
        db.execute.return_value.all.return_value = [(checkin, member)]

        buffer, filename = export_checkins_csv(db, date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
        rows = _parse_csv_bytes(buffer)
        assert len(rows) == 1
        assert rows[0]["origem"] == "catraca"
        assert "2026-03-01" in filename

    def test_no_date_filter(self):
        db = MagicMock()
        db.execute.return_value.all.return_value = []
        buffer, filename = export_checkins_csv(db)
        assert date.today().isoformat() in filename


class TestExportTemplates:
    def test_members_template(self):
        buffer, filename = export_members_template_csv()
        assert filename == "template_members.csv"
        rows = _parse_csv_bytes(buffer)
        assert len(rows) == 1
        assert rows[0]["nome"] == "Joao Silva"

    def test_checkins_template(self):
        buffer, filename = export_checkins_template_csv()
        assert filename == "template_checkins.csv"
        rows = _parse_csv_bytes(buffer)
        assert len(rows) == 1
