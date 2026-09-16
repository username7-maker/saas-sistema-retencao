import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models import Member
from app.services.retention_exclusion_service import normalize_plan_name, retention_eligible_condition
from app.services.export_service import export_retention_csv


def test_normalize_plan_name_ignores_accents_case_and_repeated_spaces():
    assert normalize_plan_name("  PLÁNO   Sênior  ") == "plano senior"


def test_retention_eligibility_covers_member_and_normalized_plan():
    gym_id = uuid.uuid4()
    compiled = str(select(Member.id).where(retention_eligible_condition(gym_id=gym_id)))

    assert "retention_exclusions" in compiled
    assert "member_id = members.id" in compiled
    assert "normalized_plan_name" in compiled
    assert "translate(trim(members.plan_name)" in compiled


@patch("app.services.export_service.get_retention_queue")
def test_retention_csv_exports_filtered_rows_and_escapes_formula_prefixes(mock_queue):
    mock_queue.return_value = SimpleNamespace(
        items=[
            SimpleNamespace(
                full_name="=Aluno perigoso",
                phone="+5511999999999",
                email="aluno@example.com",
                plan_name="Plano Premium",
                days_without_checkin=17,
                last_checkin_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
                retention_stage_label="Recuperar esta semana",
                risk_level=SimpleNamespace(value="red"),
                risk_score=84,
                churn_type="involuntary_inactivity",
                last_contact_at=None,
                next_action="Ligar",
                recommended_owner_role="receptionist",
            )
        ]
    )

    db = MagicMock()
    buffer, filename = export_retention_csv(db, search="Aluno", level="red")
    content = buffer.getvalue().decode("utf-8-sig")

    assert filename == "retencao-2026-09-16.csv"
    assert "Nome,Celular,E-mail,Plano,Dias sem treinar" in content
    assert "'=Aluno perigoso" in content
    assert "'+5511999999999" in content
    mock_queue.assert_called_once_with(
        db,
        page=1,
        page_size=100_000,
        search="Aluno",
        level="red",
        member_status="all",
        churn_type=None,
        plan_cycle=None,
        preferred_shift=None,
        retention_stage=None,
    )
