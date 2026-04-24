import json
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import AITriageRecommendation, RiskLevel
from app.services.ai_triage_service import (
    get_ai_triage_metrics_summary,
    prepare_ai_triage_recommendation_action,
    _build_onboarding_snapshot,
    _build_retention_snapshot,
    serialize_ai_triage_recommendation,
    sync_ai_triage_recommendations,
    update_ai_triage_recommendation_outcome,
    update_ai_triage_recommendation_approval,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


def test_build_retention_snapshot_maps_playbook_and_priority():
    member = SimpleNamespace(
        id=uuid4(),
        assigned_user_id=uuid4(),
        assigned_user=SimpleNamespace(full_name="Manager Teste"),
    )
    item = SimpleNamespace(
        member_id=str(member.id),
        full_name="Ana Retencao",
        risk_level=RiskLevel.RED,
        risk_score=82,
        nps_last_score=5,
        forecast_60d=35,
        days_without_checkin=16,
        last_contact_at=None,
        signals_summary="16 dias sem check-in e NPS baixo.",
        next_action="Ligar hoje",
        churn_type="voluntary_dissatisfaction",
        playbook_steps=[
            SimpleNamespace(
                action="call",
                owner="manager",
                title="Ligacao urgente - aluno em risco",
                message="Ola {nome}, quero entender o que travou sua rotina.",
            )
        ],
    )

    snapshot = _build_retention_snapshot(item, member)

    assert snapshot["source_domain"] == "retention"
    assert snapshot["recommended_channel"] == "call"
    assert snapshot["recommended_owner"]["user_id"] == member.assigned_user_id
    assert snapshot["recommended_owner"]["label"] == "Manager Teste"
    assert snapshot["suggested_message"] == "Ola Ana Retencao, quero entender o que travou sua rotina."
    assert snapshot["priority_score"] == 100
    assert snapshot["priority_bucket"] == "critical"


def test_build_retention_snapshot_is_json_serializable():
    member = SimpleNamespace(
        id=uuid4(),
        assigned_user_id=uuid4(),
        assigned_user=SimpleNamespace(full_name="Manager Teste"),
    )
    item = SimpleNamespace(
        member_id=str(member.id),
        full_name="Ana Retencao",
        risk_level=RiskLevel.RED,
        risk_score=82,
        nps_last_score=5,
        forecast_60d=35,
        days_without_checkin=16,
        last_contact_at=None,
        signals_summary="16 dias sem check-in e NPS baixo.",
        next_action="Ligar hoje",
        churn_type="voluntary_dissatisfaction",
        playbook_steps=[],
    )

    snapshot = _build_retention_snapshot(item, member)

    json.dumps(snapshot, default=str)


def test_build_onboarding_snapshot_prioritizes_missing_assessment():
    member = SimpleNamespace(
        id=uuid4(),
        full_name="Bruno Onboarding",
        phone="11999999999",
        assigned_user_id=uuid4(),
        assigned_user=SimpleNamespace(full_name="Coach Onboarding"),
        last_checkin_at=None,
    )

    snapshot = _build_onboarding_snapshot(
        member=member,
        score=32,
        status="at_risk",
        days_since_join=9,
        has_assessment=False,
        total_tasks=4,
        completed_tasks=1,
    )

    assert snapshot["source_domain"] == "onboarding"
    assert snapshot["recommended_action"] == "Concluir primeira avaliacao de onboarding"
    assert snapshot["recommended_channel"] == "task"
    assert snapshot["recommended_owner"]["role"] == "coach"
    assert snapshot["priority_bucket"] in {"high", "critical"}
    assert "Primeira avaliacao ainda nao registrada." in snapshot["why_now_details"]


def test_build_onboarding_snapshot_is_json_serializable():
    member = SimpleNamespace(
        id=uuid4(),
        full_name="Bruno Onboarding",
        phone="11999999999",
        assigned_user_id=uuid4(),
        assigned_user=SimpleNamespace(full_name="Coach Onboarding"),
        last_checkin_at=None,
    )

    snapshot = _build_onboarding_snapshot(
        member=member,
        score=32,
        status="at_risk",
        days_since_join=9,
        has_assessment=False,
        total_tasks=4,
        completed_tasks=1,
    )

    json.dumps(snapshot, default=str)


def test_sync_ai_triage_recommendations_refreshes_match_and_deactivates_stale(monkeypatch):
    gym_id = uuid4()
    member_id = uuid4()
    stale_id = uuid4()

    fresh_snapshot = {
        "source_domain": "retention",
        "source_entity_kind": "member",
        "source_entity_id": member_id,
        "member_id": member_id,
        "lead_id": None,
        "subject_name": "Ana",
        "priority_score": 91,
        "priority_bucket": "critical",
        "why_now_summary": "Aluno em risco agora.",
        "why_now_details": ["Risco vermelho."],
        "recommended_action": "Ligar hoje",
        "recommended_channel": "call",
        "recommended_owner": {"user_id": None, "role": "manager", "label": "Manager"},
        "suggested_message": "Ola Ana",
        "expected_impact": "Reduzir cancelamento.",
        "metadata": {"risk_level": "red"},
    }

    existing_match = AITriageRecommendation(
        id=uuid4(),
        gym_id=gym_id,
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=member_id,
        member_id=member_id,
        priority_score=50,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={"old": True},
    )
    stale = AITriageRecommendation(
        id=uuid4(),
        gym_id=gym_id,
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=stale_id,
        member_id=stale_id,
        priority_score=40,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={"stale": True},
    )

    monkeypatch.setattr("app.services.ai_triage_service._build_retention_snapshots", lambda *_args, **_kwargs: [fresh_snapshot])
    monkeypatch.setattr("app.services.ai_triage_service._build_onboarding_snapshots", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **_kwargs: None)

    db = MagicMock()
    db.scalars.side_effect = [
        _ScalarResult([existing_match, stale]),
        _ScalarResult([existing_match]),
    ]
    db.scalar.return_value = 1

    result = sync_ai_triage_recommendations(db, gym_id=gym_id, limit_per_domain=10)

    assert len(result) == 1
    assert existing_match.priority_score == 91
    assert existing_match.payload_snapshot["subject_name"] == "Ana"
    assert isinstance(existing_match.payload_snapshot["source_entity_id"], str)
    assert isinstance(existing_match.payload_snapshot["member_id"], str)
    json.dumps(existing_match.payload_snapshot)
    assert existing_match.is_active is True
    assert stale.is_active is False
    assert db.flush.called


def test_serialize_ai_triage_recommendation_reads_snapshot_contract():
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=72,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Carla",
            "priority_bucket": "high",
            "why_now_summary": "Onboarding exige acao.",
            "why_now_details": ["Dia 8 do onboarding."],
            "recommended_action": "Contato humano imediato para destravar onboarding",
            "recommended_channel": "whatsapp",
            "recommended_owner": {"user_id": None, "role": "reception", "label": "Recepcao"},
            "suggested_message": "Ola Carla",
            "expected_impact": "Reduzir dropout.",
            "metadata": {"onboarding_score": 45},
        },
    )

    serialized = serialize_ai_triage_recommendation(recommendation)

    assert serialized.subject_name == "Carla"
    assert serialized.recommended_owner is not None
    assert serialized.recommended_owner.label == "Recepcao"
    assert serialized.metadata["onboarding_score"] == 45
    assert serialized.operator_summary == "Onboarding exige acao."
    assert serialized.primary_action_type == "prepare_outbound_message"
    assert serialized.primary_action_label == "Preparar WhatsApp"
    assert serialized.requires_explicit_approval is False
    assert serialized.show_outcome_step is False


def test_update_ai_triage_recommendation_approval_marks_approved(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=88,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Ana",
            "why_now_summary": "Risco elevado.",
            "recommended_action": "Ligar hoje",
            "expected_impact": "Evitar churn.",
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = update_ai_triage_recommendation_approval(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        decision="approved",
        current_user=current_user,
        note="Pronto para contato.",
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert response.approval_state == "approved"
    assert recommendation.suggestion_state == "reviewed"
    assert recommendation.execution_state == "pending"
    assert recommendation.outcome_state == "pending"
    assert audit_calls[0]["action"] == "ai_triage_recommendation_approved"
    db.flush.assert_called_once()


def test_update_ai_triage_recommendation_approval_marks_rejected(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=61,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Bruno",
            "why_now_summary": "Onboarding travado.",
            "recommended_action": "Revisar manualmente",
            "expected_impact": "Retomar jornada.",
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = update_ai_triage_recommendation_approval(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        decision="rejected",
        current_user=current_user,
        note="Sem contexto suficiente.",
    )

    assert response.approval_state == "rejected"
    assert recommendation.suggestion_state == "reviewed"
    assert recommendation.execution_state == "blocked"
    assert recommendation.outcome_state == "dismissed"
    assert audit_calls[0]["action"] == "ai_triage_recommendation_rejected"
    assert audit_calls[0]["details"]["note"] == "Sem contexto suficiente."


def test_prepare_ai_triage_recommendation_action_creates_task(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=92,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="approved",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Ana",
            "priority_bucket": "critical",
            "why_now_summary": "Risco elevado.",
            "why_now_details": ["16 dias sem check-in."],
            "recommended_action": "Ligar hoje",
            "recommended_channel": "call",
            "recommended_owner": {"user_id": None, "role": "manager", "label": "Manager"},
            "suggested_message": "Oi Ana",
            "expected_impact": "Evitar churn.",
            "metadata": {},
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    monkeypatch.setattr(
        "app.services.ai_triage_service.create_task",
        lambda *_args, **_kwargs: SimpleNamespace(
            id=uuid4(),
            priority=SimpleNamespace(value="urgent"),
            status=SimpleNamespace(value="todo"),
        ),
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = prepare_ai_triage_recommendation_action(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        action="create_task",
        current_user=current_user,
        note="Criar task hoje",
    )

    assert response.supported is True
    assert response.task_id is not None
    assert response.recommendation.execution_state == "prepared"
    assert response.metadata["prepared_action"] == "create_task"
    assert audit_calls[-1]["action"] == "ai_triage_action_prepared"
    db.flush.assert_called_once()


def test_prepare_ai_triage_recommendation_action_auto_approves_normal_item(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=58,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Bruno",
            "priority_bucket": "medium",
            "why_now_summary": "Primeiro follow-up do onboarding ainda nao aconteceu.",
            "recommended_action": "Preparar contato de onboarding",
            "recommended_channel": "whatsapp",
            "recommended_owner": {"user_id": None, "role": "reception", "label": "Recepcao"},
            "suggested_message": "Ola Bruno",
            "expected_impact": "Retomar jornada.",
            "metadata": {},
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = prepare_ai_triage_recommendation_action(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        action="prepare_outbound_message",
        current_user=current_user,
        auto_approve=True,
        operator_note="Pode seguir agora.",
    )

    assert response.supported is True
    assert response.prepared_message == "Ola Bruno"
    assert recommendation.approval_state == "approved"
    assert recommendation.execution_state == "prepared"
    assert audit_calls[0]["action"] == "ai_triage_recommendation_approved"
    assert audit_calls[-1]["action"] == "ai_triage_action_prepared"


def test_prepare_ai_triage_recommendation_action_requires_explicit_confirmation_for_critical_item(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=92,
        is_active=True,
        suggestion_state="suggested",
        approval_state="pending",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Ana",
            "priority_bucket": "critical",
            "why_now_summary": "Risco elevado.",
            "recommended_action": "Ligar hoje",
            "recommended_channel": "call",
            "recommended_owner": {"user_id": None, "role": "manager", "label": "Manager"},
            "suggested_message": "Oi Ana",
            "expected_impact": "Evitar churn.",
            "metadata": {},
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        prepare_ai_triage_recommendation_action(
            db,
            recommendation_id=recommendation.id,
            gym_id=recommendation.gym_id,
            action="prepare_outbound_message",
            current_user=current_user,
            auto_approve=True,
        )
    assert exc_info.value.status_code == 409

def test_prepare_ai_triage_recommendation_action_reports_unavailable_job(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=64,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="approved",
        execution_state="pending",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Bruno",
            "recommended_action": "Revisar onboarding",
            "expected_impact": "Retomar jornada.",
            "metadata": {},
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = prepare_ai_triage_recommendation_action(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        action="enqueue_approved_job",
        current_user=current_user,
    )

    assert response.supported is False
    assert recommendation.execution_state == "pending"
    assert audit_calls[-1]["action"] == "ai_triage_action_unavailable"


def test_update_ai_triage_recommendation_outcome_marks_execution_completed(monkeypatch):
    recommendation = AITriageRecommendation(
        id=uuid4(),
        gym_id=uuid4(),
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=75,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="approved",
        execution_state="prepared",
        outcome_state="pending",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={
            "subject_name": "Carla",
            "recommended_action": "Enviar follow-up",
            "expected_impact": "Retomar contato.",
            "metadata": {},
        },
    )
    current_user = SimpleNamespace(id=uuid4(), gym_id=recommendation.gym_id)
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.ai_triage_service.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.services.ai_triage_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = update_ai_triage_recommendation_outcome(
        db,
        recommendation_id=recommendation.id,
        gym_id=recommendation.gym_id,
        outcome="positive",
        current_user=current_user,
        note="Aluno respondeu.",
    )

    assert response.outcome_state == "positive"
    assert response.execution_state == "completed"
    assert audit_calls[-1]["action"] == "ai_triage_outcome_updated"


def test_get_ai_triage_metrics_summary_aggregates_current_state_and_audit_window():
    gym_id = uuid4()
    recommendation_one = AITriageRecommendation(
        id=uuid4(),
        gym_id=gym_id,
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=90,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="approved",
        execution_state="prepared",
        outcome_state="positive",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={"subject_name": "Ana"},
    )
    recommendation_two = AITriageRecommendation(
        id=uuid4(),
        gym_id=gym_id,
        source_domain="onboarding",
        source_entity_kind="member",
        source_entity_id=uuid4(),
        member_id=uuid4(),
        priority_score=55,
        is_active=True,
        suggestion_state="reviewed",
        approval_state="rejected",
        execution_state="blocked",
        outcome_state="dismissed",
        last_refreshed_at=datetime.now(tz=timezone.utc),
        payload_snapshot={"subject_name": "Bruno"},
    )
    audit_rows = [
        SimpleNamespace(
            entity_id=recommendation_one.id,
            action="ai_triage_recommendation_suggested",
            created_at=datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            entity_id=recommendation_one.id,
            action="ai_triage_recommendation_approved",
            created_at=datetime(2026, 4, 18, 9, 10, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            entity_id=recommendation_one.id,
            action="ai_triage_action_prepared",
            created_at=datetime(2026, 4, 18, 9, 15, tzinfo=timezone.utc),
        ),
    ]
    db = MagicMock()
    db.scalars.side_effect = [
        _ScalarResult([recommendation_one, recommendation_two]),
        _ScalarResult(audit_rows),
    ]

    summary = get_ai_triage_metrics_summary(db, gym_id=gym_id)

    assert summary.total_active == 2
    assert summary.approved_total == 1
    assert summary.rejected_total == 1
    assert summary.prepared_action_total == 1
    assert summary.positive_outcome_total == 1
    assert summary.acceptance_rate == 0.5
    assert summary.same_day_prepared_total == 1
    assert summary.average_time_to_approval_seconds == 600
