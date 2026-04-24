import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.models import LeadStage
from app.routers.public import public_whatsapp_webhook
from app.routers.sales import call_event_endpoint
from app.schemas.sales import CallEventCreate, PublicBookingConfirmRequest
from app.services.booking_service import confirm_public_booking, process_booking_reminders
from app.services.call_script_service import register_call_event
from app.services.nurturing_service import handle_incoming_whatsapp_webhook
from app.services.sales_brief_service import _generate_cached_sales_ai, get_sales_brief


def _mock_scalars(items):
    result = MagicMock()
    result.all.return_value = items
    return result


def _build_request(query_string: bytes = b"") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": "/api/v1/public/whatsapp/webhook",
        "raw_path": b"/api/v1/public/whatsapp/webhook",
        "query_string": query_string,
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_sales_brief_with_diagnosis_returns_diagnosis_data(monkeypatch):
    lead_id = uuid4()
    lead = SimpleNamespace(
        id=lead_id,
        full_name="Academia Centro",
        email="lead@test.com",
        phone="5511999999999",
        source="public_diagnostico",
        stage=LeadStage.PROPOSAL,
        notes=[],
        deleted_at=None,
    )
    sequence = SimpleNamespace(
        diagnosis_data={
            "gym_name": "Academia Centro",
            "total_members": 320,
            "avg_monthly_fee": 189.9,
            "red_total": 12,
            "yellow_total": 8,
            "mrr_at_risk": 3780.0,
            "annual_loss_projection": 45360.0,
            "estimated_recovered_members": 7,
            "estimated_preserved_annual_revenue": 15876.0,
        },
        created_at=datetime.now(tz=timezone.utc) - timedelta(days=2),
        current_step=1,
        completed=False,
    )
    db = MagicMock()
    db.scalar.side_effect = [lead, sequence]
    db.scalars.side_effect = [_mock_scalars([]), _mock_scalars([]), _mock_scalars([])]

    brief = get_sales_brief(db, lead_id)

    assert brief["diagnosis"]["has_diagnosis"] is True
    assert brief["diagnosis"]["red_total"] == 12
    assert brief["profile"]["gym_name"] == "Academia Centro"


def test_sales_brief_without_diagnosis_returns_message():
    lead_id = uuid4()
    lead = SimpleNamespace(
        id=lead_id,
        full_name="Lead sem diagnostico",
        email=None,
        phone=None,
        source="manual",
        stage=LeadStage.NEW,
        notes=[],
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.side_effect = [lead, None]
    db.scalars.side_effect = [_mock_scalars([]), _mock_scalars([]), _mock_scalars([])]

    brief = get_sales_brief(db, lead_id)

    assert brief["diagnosis"]["has_diagnosis"] is False
    assert "sem diagnostico" in brief["diagnosis"]["message"].lower()


def test_sales_brief_missing_lead_returns_404():
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_sales_brief(db, uuid4())

    assert exc.value.status_code == 404


def test_sales_brief_ai_arguments_are_cached(monkeypatch):
    from app.services import sales_brief_service

    lead = SimpleNamespace(id=uuid4(), full_name="Lead Cache", source="public_diagnostico", stage=LeadStage.PROPOSAL)
    diagnosis = {"has_diagnosis": True, "mrr_at_risk": 2000.0, "red_total": 4, "annual_loss_projection": 24000.0}
    history = []
    cache_key = sales_brief_service.make_cache_key("sales_brief", lead.id)
    sales_brief_service.dashboard_cache.delete(cache_key)

    calls = {"count": 0}

    class FakeMessages:
        def create(self, **_kwargs):
            calls["count"] += 1
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        text='{"arguments":[{"title":"ROI imediato","body":"Use os numeros do diagnostico.","usage":"Na abertura"},{"title":"Automacao","body":"Reduz trabalho manual.","usage":"Quando falar de operacao"},{"title":"Churn","body":"Mostre custo da inacao.","usage":"No fechamento"}],"next_step":"enviar_proposta_apos_call"}'
                    )
                ]
            )

    class FakeAnthropic:
        def __init__(self, **_kwargs):
            self.messages = FakeMessages()

    monkeypatch.setattr("app.services.sales_brief_service.settings.claude_api_key", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))

    first = _generate_cached_sales_ai(lead, diagnosis, history)
    second = _generate_cached_sales_ai(lead, diagnosis, history)

    assert first["next_step"] == "enviar_proposta_apos_call"
    assert second["next_step"] == "enviar_proposta_apos_call"
    assert calls["count"] == 1


def test_whatsapp_message_with_known_objection_generates_auto_response(monkeypatch):
    lead = SimpleNamespace(id=uuid4(), notes=[])
    sequence = SimpleNamespace(lead_id=lead.id, gym_id=uuid4(), diagnosis_data={"mrr_at_risk": 3000}, prospect_whatsapp="5511999999999")
    db = MagicMock()
    db.get.return_value = lead

    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: sequence)
    monkeypatch.setattr(
        "app.services.nurturing_service.generate_objection_response",
        lambda *_args, **_kwargs: {
            "matched": True,
            "objection_id": uuid4(),
            "response_text": "O ROI cobre o investimento.",
            "source": "keyword_rule",
        },
    )
    monkeypatch.setattr(
        "app.services.nurturing_service.send_whatsapp_sync",
        lambda *_args, **_kwargs: SimpleNamespace(status="sent"),
    )

    result = handle_incoming_whatsapp_webhook(
        db,
        {
            "event": "message.received",
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False, "id": "msg-1"},
                "message": {"conversation": "Achei caro o investimento"},
            },
        },
    )

    assert result["processed"] is True
    assert "respondida" in result["detail"].lower()
    assert any(note["type"] == "objection_detected" for note in lead.notes)


def test_whatsapp_message_without_objection_is_only_logged(monkeypatch):
    sequence = SimpleNamespace(lead_id=uuid4(), gym_id=uuid4(), diagnosis_data={}, prospect_whatsapp="5511999999999")
    db = MagicMock()

    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: sequence)
    monkeypatch.setattr(
        "app.services.nurturing_service.generate_objection_response",
        lambda *_args, **_kwargs: {"matched": False, "objection_id": None, "response_text": "", "source": "generic"},
    )

    result = handle_incoming_whatsapp_webhook(
        db,
        {
            "event": "message.received",
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Recebi o material, obrigado"},
            },
        },
    )

    assert result["processed"] is True
    assert "sem objecao" in result["detail"].lower()


def test_whatsapp_invalid_token_returns_401(monkeypatch):
    monkeypatch.setattr("app.routers.public.settings.whatsapp_webhook_token", "secret")

    with pytest.raises(HTTPException) as exc:
        public_whatsapp_webhook(
            payload={},
            request=_build_request(),
            db=MagicMock(),
            x_webhook_token="wrong",
            authorization=None,
        )

    assert exc.value.status_code == 401


def test_whatsapp_query_token_is_not_accepted(monkeypatch):
    monkeypatch.setattr("app.routers.public.settings.whatsapp_webhook_token", "secret")

    with pytest.raises(HTTPException) as exc:
        public_whatsapp_webhook(
            payload={},
            request=_build_request(query_string=b"token=secret"),
            db=MagicMock(),
            x_webhook_token=None,
            authorization=None,
        )

    assert exc.value.status_code == 401


def test_whatsapp_message_without_active_sequence_is_ignored(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: None)

    result = handle_incoming_whatsapp_webhook(
        db,
        {
            "event": "message.received",
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Ola"},
            },
        },
    )

    assert result["processed"] is False
    assert "sequencia ativa" in result["detail"].lower()


def test_whatsapp_message_without_sequence_but_with_member_registers_response(monkeypatch):
    gym_id = uuid4()
    member = SimpleNamespace(id=uuid4(), gym_id=gym_id, phone="(11) 99999-9999")
    db = MagicMock()
    recorded: list = []

    monkeypatch.setattr("app.services.nurturing_service.find_active_sequence_by_phone", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.services.nurturing_service._find_member_by_phone",
        lambda _db, gid, phone: member if gid == gym_id else None,
    )
    monkeypatch.setattr(
        "app.services.nurturing_service._record_member_inbound_response",
        lambda *_args, **kwargs: recorded.append(kwargs["member"].id),
    )

    result = handle_incoming_whatsapp_webhook(
        db,
        {
            "instance": "gym_test",
            "event": "message.received",
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Oi, posso treinar hoje?"},
            },
        },
        gym_id=gym_id,
    )

    assert result["processed"] is True
    assert "aluno" in result["detail"].lower()
    assert recorded == [member.id]
    assert db.commit.called


def test_booking_confirmation_updates_stage_and_pauses_sequence(monkeypatch):
    lead = SimpleNamespace(
        id=uuid4(),
        gym_id=uuid4(),
        stage=LeadStage.NEW,
        last_contact_at=None,
        notes=[],
        phone="5511999999999",
        email="lead@test.com",
        deleted_at=None,
    )
    booking = SimpleNamespace(
        id=uuid4(),
        provider_name="cal",
        scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
        prospect_whatsapp="5511999999999",
        status="confirmed",
    )
    db = MagicMock()
    pause_calls = []

    monkeypatch.setattr("app.services.booking_service._resolve_public_gym_id", lambda: lead.gym_id)
    monkeypatch.setattr("app.services.booking_service._resolve_or_create_public_lead", lambda *_args, **_kwargs: lead)
    monkeypatch.setattr("app.services.booking_service._upsert_booking", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr("app.services.booking_service._send_booking_confirmation_whatsapp", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.booking_service.pause_sequences_for_lead", lambda *_args, **_kwargs: pause_calls.append(True))

    saved_lead, saved_booking = confirm_public_booking(
        db,
        PublicBookingConfirmRequest(
            lead_id=lead.id,
            prospect_name="Lead Booking",
            email="lead@test.com",
            whatsapp="5511999999999",
            scheduled_for=booking.scheduled_for,
            provider_name="cal",
            provider_booking_id="booking-1",
        ),
    )

    assert saved_lead.stage == LeadStage.MEETING_SCHEDULED
    assert saved_booking.id == booking.id
    assert len(pause_calls) == 1


def test_booking_reminder_job_sends_one_hour_before(monkeypatch):
    lead_id = uuid4()
    booking = SimpleNamespace(
        id=uuid4(),
        lead_id=lead_id,
        status="confirmed",
        reminder_sent_at=None,
        scheduled_for=datetime.now(tz=timezone.utc) + timedelta(minutes=58),
        prospect_whatsapp="5511999999999",
    )
    lead = SimpleNamespace(id=lead_id, phone="5511999999999")
    db = MagicMock()
    db.scalars.return_value = _mock_scalars([booking])
    db.get.return_value = lead

    monkeypatch.setattr(
        "app.services.booking_service.send_whatsapp_sync",
        lambda *_args, **_kwargs: SimpleNamespace(status="sent"),
    )

    result = process_booking_reminders(db)

    assert result["processed"] == 1
    assert result["sent"] == 1
    assert booking.reminder_sent_at is not None


def test_booking_for_missing_lead_creates_or_ignores_cleanly(monkeypatch):
    created_lead = SimpleNamespace(id=uuid4(), gym_id=uuid4(), phone="5511999999999", email="new@test.com", notes=[], stage=LeadStage.NEW)
    db = MagicMock()
    db.get.return_value = None
    db.scalar.return_value = None

    monkeypatch.setattr("app.services.booking_service.create_public_booking_lead", lambda *_args, **_kwargs: created_lead)

    from app.services.booking_service import _resolve_or_create_public_lead

    lead = _resolve_or_create_public_lead(
        db,
        created_lead.gym_id,
        PublicBookingConfirmRequest(
            prospect_name="Novo Prospect",
            email="new@test.com",
            whatsapp="5511999999999",
            scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=1),
        ),
    )

    assert lead.id == created_lead.id


def test_proposal_requested_event_returns_durable_job_metadata(monkeypatch):
    gym_id = uuid4()
    lead = SimpleNamespace(id=uuid4(), gym_id=gym_id, stage=LeadStage.PROPOSAL_SENT)
    current_user = SimpleNamespace(id=uuid4(), gym_id=gym_id, role="salesperson")
    job_id = uuid4()
    db = MagicMock()

    monkeypatch.setattr("app.routers.sales.register_call_event", lambda *_args, **_kwargs: lead)
    monkeypatch.setattr(
        "app.routers.sales.enqueue_lead_proposal_dispatch_job",
        lambda *_args, **_kwargs: (SimpleNamespace(id=job_id, status="pending"), True),
    )
    monkeypatch.setattr("app.routers.sales.dispatch_lead_post_commit_effects", lambda *_args, **_kwargs: None)

    response = call_event_endpoint(
        lead_id=lead.id,
        payload=CallEventCreate(event_type="proposal_requested"),
        response=Response(),
        db=db,
        current_user=current_user,
    )

    assert response.lead_id == lead.id
    assert response.job_id == job_id
    assert response.job_status == "pending"
    db.commit.assert_called_once()


def test_lost_event_updates_stage_and_logs_audit(monkeypatch):
    lead = SimpleNamespace(
        id=uuid4(),
        gym_id=uuid4(),
        stage=LeadStage.PROPOSAL,
        lost_reason=None,
        last_contact_at=None,
        notes=[],
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = lead
    audit_calls = []

    monkeypatch.setattr("app.services.call_script_service.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    updated = register_call_event(
        db,
        lead_id=lead.id,
        payload=CallEventCreate(event_type="lost", lost_reason="Sem orcamento"),
    )

    assert updated.stage == LeadStage.LOST
    assert updated.lost_reason == "Sem orcamento"
    assert audit_calls[0]["action"] == "call_event_logged"


def test_close_now_uses_uncommitted_lead_update_and_commits_in_caller(monkeypatch):
    lead = SimpleNamespace(
        id=uuid4(),
        gym_id=uuid4(),
        stage=LeadStage.PROPOSAL,
        lost_reason=None,
        last_contact_at=None,
        notes=[],
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = lead
    update_calls = []
    dispatch_calls = []

    def _update_lead(_db, lead_id, payload, *, commit=True):
        update_calls.append({"lead_id": lead_id, "stage": payload.stage, "commit": commit})
        lead.stage = payload.stage
        return lead

    def _dispatch_post_commit(updated_lead):
        assert db.commit.called
        dispatch_calls.append(updated_lead.id)

    monkeypatch.setattr("app.services.call_script_service.update_lead", _update_lead)
    monkeypatch.setattr("app.services.call_script_service.log_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.services.call_script_service.dispatch_lead_post_commit_effects", _dispatch_post_commit)

    updated = register_call_event(
        db,
        lead_id=lead.id,
        payload=CallEventCreate(event_type="close_now"),
    )

    assert updated.stage == LeadStage.WON
    assert update_calls == [{"lead_id": lead.id, "stage": LeadStage.WON, "commit": False}]
    db.commit.assert_called_once()
    assert dispatch_calls == [lead.id]
