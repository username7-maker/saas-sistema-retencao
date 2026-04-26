from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import LeadStage, MemberStatus, RiskLevel, RoleEnum
from app.services.member_intelligence_service import build_lead_to_member_intelligence_context
from tests.conftest import GYM_ID, MEMBER_ID, USER_ID


def _member(**overrides):
    data = {
        "id": MEMBER_ID,
        "full_name": "Aluno Integrado",
        "email": "aluno@teste.com",
        "phone": "11999999999",
        "status": MemberStatus.ACTIVE,
        "plan_name": "Plano Mensal",
        "monthly_fee": Decimal("199.90"),
        "join_date": date(2026, 4, 1),
        "preferred_shift": "morning",
        "assigned_user_id": USER_ID,
        "is_vip": False,
        "extra_data": {
            "consents": {
                "lgpd": True,
                "communication": False,
                "image": True,
                "contract": True,
            }
        },
        "onboarding_status": "active",
        "onboarding_score": 84,
        "retention_stage": "onboarding",
        "churn_type": None,
        "loyalty_months": 1,
        "last_checkin_at": datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc),
        "risk_level": RiskLevel.GREEN,
        "risk_score": 20,
        "nps_last_score": 9,
        "updated_at": datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _context(**overrides):
    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    payload = {
        "member": _member(),
        "lead": SimpleNamespace(
            id="44444444-4444-4444-4444-444444444444",
            source="instagram",
            stage=LeadStage.WON,
            owner_id=USER_ID,
            converted_member_id=MEMBER_ID,
            last_contact_at=now - timedelta(days=20),
            estimated_value=Decimal("597.00"),
            acquisition_cost=Decimal("32.50"),
            notes=[{"text": "Visitou unidade"}],
        ),
        "checkins_30d": 8,
        "checkins_90d": 18,
        "latest_checkin_at": now - timedelta(days=2),
        "assessments_total": 1,
        "latest_assessment": SimpleNamespace(assessment_date=now - timedelta(days=10)),
        "body_composition_total": 1,
        "latest_body_composition": SimpleNamespace(
            measured_at=now - timedelta(days=8),
            evaluation_date=date(2026, 4, 18),
            body_fat_percent=Decimal("22.30"),
            skeletal_muscle_kg=Decimal("31.10"),
            muscle_mass_kg=None,
            weight_kg=Decimal("78.40"),
        ),
        "open_tasks_total": 2,
        "overdue_tasks_total": 0,
        "next_task_due_at": now + timedelta(days=1),
        "latest_completed_task_at": now - timedelta(days=3),
        "open_alerts_total": 0,
        "generated_at": now,
    }
    payload.update(overrides)
    return build_lead_to_member_intelligence_context(**payload)


def test_intelligence_context_preserves_lead_origin_and_consent():
    result = _context()

    assert result.member.member_id == MEMBER_ID
    assert result.lead is not None
    assert result.lead.source == "instagram"
    assert result.lead.stage == "won"
    assert result.consent.lgpd is True
    assert result.consent.communication is False
    assert result.consent.missing == []
    assert result.activity.checkins_30d == 8
    assert result.assessment.latest_muscle_mass_kg == 31.1
    assert "missing_lead_origin" not in result.data_quality_flags


def test_intelligence_context_flags_missing_operational_inputs():
    result = _context(
        member=_member(preferred_shift=None, extra_data={}),
        lead=None,
        checkins_30d=0,
        checkins_90d=0,
        latest_checkin_at=None,
        assessments_total=0,
        latest_assessment=None,
        body_composition_total=0,
        latest_body_composition=None,
    )

    assert result.lead is None
    assert "missing_lead_origin" in result.data_quality_flags
    assert "missing_lgpd_consent" in result.data_quality_flags
    assert "missing_preferred_shift" in result.data_quality_flags
    assert "missing_assessment" in result.data_quality_flags
    assert "missing_body_composition" in result.data_quality_flags


def _trainer_user():
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        full_name="Professor Teste",
        email="professor@teste.com",
        role=RoleEnum.TRAINER,
        is_active=True,
        deleted_at=None,
    )


def test_trainer_can_read_member_intelligence_context(app, client):
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()
    app.dependency_overrides[get_current_user] = _trainer_user

    try:
        with patch("app.routers.members.get_member_intelligence_context", return_value=_context()) as service_mock:
            response = client.get(f"/api/v1/members/{MEMBER_ID}/intelligence-context")

        assert response.status_code == 200
        assert response.json()["lead"]["source"] == "instagram"
        assert service_mock.call_args.kwargs["gym_id"] == GYM_ID
    finally:
        app.dependency_overrides.clear()
