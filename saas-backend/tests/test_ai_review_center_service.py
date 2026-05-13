import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import AutopilotAction, RoleEnum
from app.schemas.ai_review_center import AiReviewCenterFeedbackInput, AiReviewCenterItemOut
from app.services import ai_review_center_service as service


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
ACTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _action() -> AutopilotAction:
    now = datetime.now(tz=timezone.utc)
    action = AutopilotAction(
        id=ACTION_ID,
        gym_id=GYM_ID,
        policy_key="ai_service_agent_retention",
        domain="retention",
        action_type=service.AI_SERVICE_AGENT_ACTION_TYPE,
        status="draft_ready",
        member_id=MEMBER_ID,
        channel="kommo",
        message_body="Oi! Posso te ajudar a voltar essa semana?",
        metadata_json={"intent": "retention", "evidence": ["kommo_inbound"]},
    )
    action.created_at = now
    action.updated_at = now
    return action


def _item(action: AutopilotAction) -> AiReviewCenterItemOut:
    return AiReviewCenterItemOut(
        source_type="ai_service_agent",
        source_id=action.id,
        status=action.status,
        domain=action.domain,
        channel=action.channel,
        subject_name="Ana Silva",
        member_id=action.member_id,
        lead_id=None,
        intent="retention",
        sensitivity="normal",
        summary="Resumo",
        received_message="Quero voltar",
        draft_reply=action.message_body,
        next_action="Revisar",
        recommended_owner_role="reception",
        blocked_reasons=[],
        evidence=["kommo_inbound"],
        badges=[],
        context_path=f"/assessments/members/{action.member_id}",
        can_prepare_kommo=True,
        can_reject=True,
        metadata=action.metadata_json,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def test_record_feedback_approved_persists_metadata_and_event(monkeypatch):
    action = _action()
    db = MagicMock()
    recorded_events = []
    monkeypatch.setattr(service, "_get_target_for_source", lambda *_args, **_kwargs: ("action", action))
    monkeypatch.setattr(service, "_item_for_source", lambda *_args, **_kwargs: _item(action))
    monkeypatch.setattr(service, "record_event", lambda *args, **kwargs: recorded_events.append(kwargs))

    result = service.record_review_center_feedback(
        db,
        gym_id=GYM_ID,
        user_role=RoleEnum.OWNER,
        reviewer_user_id=USER_ID,
        source_type="ai_service_agent",
        source_id=ACTION_ID,
        payload=AiReviewCenterFeedbackInput(decision="approved", reason="Bom para envio."),
    )

    feedback = action.metadata_json["review_center_feedback"]
    assert result.item.source_id == ACTION_ID
    assert feedback["decision"] == "approved"
    assert feedback["reviewed_by_user_id"] == str(USER_ID)
    assert recorded_events[0]["event_type"] == "ai_review_center_feedback_recorded"
    assert recorded_events[0]["metadata"]["decision"] == "approved"


def test_record_feedback_edited_updates_message_body(monkeypatch):
    action = _action()
    db = MagicMock()
    monkeypatch.setattr(service, "_get_target_for_source", lambda *_args, **_kwargs: ("action", action))
    monkeypatch.setattr(service, "_item_for_source", lambda *_args, **_kwargs: _item(action))
    monkeypatch.setattr(service, "record_event", lambda *args, **kwargs: None)

    service.record_review_center_feedback(
        db,
        gym_id=GYM_ID,
        user_role=RoleEnum.OWNER,
        reviewer_user_id=USER_ID,
        source_type="ai_service_agent",
        source_id=ACTION_ID,
        payload=AiReviewCenterFeedbackInput(
            decision="edited",
            reason="Tom mais humano.",
            edited_reply="Oi, Ana! Vi sua mensagem. Quer que eu te ajude a organizar a volta?",
        ),
    )

    assert action.message_body.startswith("Oi, Ana")
    assert action.metadata_json["review_center_feedback"]["decision"] == "edited"
    assert action.metadata_json["review_center_feedback"]["edited_reply"] == action.message_body


def test_record_feedback_requires_reason_for_escalation():
    with pytest.raises(HTTPException) as exc:
        service._validate_feedback_payload(AiReviewCenterFeedbackInput(decision="escalated"))

    assert exc.value.status_code == 422


def test_review_center_metrics_count_feedback_decisions():
    now = datetime.now(tz=timezone.utc)
    base = dict(
        source_type="ai_service_agent",
        source_id=ACTION_ID,
        status="draft_ready",
        domain="retention",
        channel="kommo",
        subject_name="Ana Silva",
        member_id=MEMBER_ID,
        lead_id=None,
        blocked_reasons=[],
        evidence=[],
        badges=[],
        can_prepare_kommo=True,
        can_reject=True,
        metadata={},
        created_at=now,
        updated_at=now,
    )
    items = [
        AiReviewCenterItemOut(**base, review_decision="approved"),
        AiReviewCenterItemOut(**{**base, "source_id": uuid.uuid4()}, review_decision="edited"),
        AiReviewCenterItemOut(**{**base, "source_id": uuid.uuid4(), "status": "cancelled"}, review_decision="rejected"),
    ]

    metrics = service._build_metrics(items)

    assert metrics.reviewed == 3
    assert metrics.approved == 1
    assert metrics.edited == 1
    assert metrics.rejected == 1
    assert metrics.utilization_rate == pytest.approx(0.6666, abs=0.0001)
