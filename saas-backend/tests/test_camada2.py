from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.models import DiagnosisError, LeadStage
from app.services.diagnosis_service import (
    classify_member_risk,
    compute_diagnosis_kpis,
    parse_diagnosis_checkins_csv,
    process_public_diagnosis_background,
)
from app.services.nurturing_service import (
    calculate_next_send_at,
    create_nurturing_sequence,
    run_nurturing_followup,
)
from app.services.objection_service import generate_objection_response


def _mock_scalar_result(items):
    result = MagicMock()
    result.all.return_value = items
    return result


def test_parse_csv_accepts_flexible_order_and_date_formats():
    csv_content = (
        "hora;nome;data\n"
        "07:10;Ana Souza;05/03/2026\n"
        "18:20;Bruno Lima;2026-03-04\n"
        "06:55;Carla Mendes;03/01/2026\n"
    ).encode("utf-8")

    analyzed = parse_diagnosis_checkins_csv(csv_content)

    assert len(analyzed) == 3
    assert {item["member_key"] for item in analyzed} == {"Ana Souza", "Bruno Lima", "Carla Mendes"}
    assert all(item["last_checkin_at"] for item in analyzed)


def test_parse_csv_member_without_checkin_is_red():
    csv_content = (
        "nome,data,hora\n"
        "Aluno Sem Checkin,,\n"
        "Aluno Ativo,2026-03-05,07:00\n"
    ).encode("utf-8")

    analyzed = parse_diagnosis_checkins_csv(csv_content)
    by_member = {item["member_key"]: item for item in analyzed}

    assert by_member["Aluno Sem Checkin"]["risk_level"] == "red"
    assert by_member["Aluno Sem Checkin"]["last_checkin_at"] is None
    assert by_member["Aluno Ativo"]["risk_level"] in {"green", "yellow", "red"}


def test_parse_csv_empty_header_only_raises():
    with pytest.raises(ValueError, match="CSV sem check-ins validos|CSV vazio ou sem cabecalho"):
        parse_diagnosis_checkins_csv(b"nome,data,hora\n")


def test_classification_rule_for_red_and_green():
    assert classify_member_risk(20, 0) == "red"
    assert classify_member_risk(2, 10) == "green"


def test_compute_kpis_for_mrr_at_risk():
    analyzed_members = [
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
        {"risk_level": "red"},
    ]

    kpis = compute_diagnosis_kpis(
        analyzed_members=analyzed_members,
        total_members=10,
        avg_monthly_fee=Decimal("200"),
    )

    assert kpis["red_total"] == 10
    assert kpis["mrr_at_risk"] == 2000.0


def test_create_nurturing_sequence_initializes_step_zero():
    db = MagicMock()

    sequence = create_nurturing_sequence(
        db,
        gym_id=uuid4(),
        lead_id=uuid4(),
        prospect_email="lead@test.com",
        prospect_whatsapp="5511999999999",
        prospect_name="Lead Teste",
        diagnosis_data={"red_total": 3},
    )

    assert sequence.current_step == 0
    assert sequence.completed is False
    assert sequence.next_send_at is not None
    db.commit.assert_called_once()


def test_calculate_next_send_at_uses_created_at_offset():
    created_at = datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc)

    assert calculate_next_send_at(created_at, 1) == created_at + timedelta(days=1)
    assert calculate_next_send_at(created_at, 7) == created_at + timedelta(days=7)
    assert calculate_next_send_at(created_at, None) is None


def test_run_nurturing_followup_completes_after_step_7(monkeypatch):
    sequence = SimpleNamespace(
        lead_id=None,
        current_step=7,
        created_at=datetime.now(tz=timezone.utc) - timedelta(days=7),
        next_send_at=datetime.now(tz=timezone.utc) - timedelta(minutes=5),
        completed=False,
        diagnosis_data={},
    )
    db = MagicMock()
    db.scalars.return_value = _mock_scalar_result([sequence])
    monkeypatch.setattr("app.services.nurturing_service._dispatch_step", lambda *_args, **_kwargs: True)

    result = run_nurturing_followup(db)

    assert result["processed"] == 1
    assert result["completed"] == 1
    assert sequence.completed is True


def test_run_nurturing_followup_stops_when_lead_won():
    lead_id = uuid4()
    sequence = SimpleNamespace(
        lead_id=lead_id,
        current_step=1,
        created_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
        next_send_at=datetime.now(tz=timezone.utc) - timedelta(minutes=5),
        completed=False,
        diagnosis_data={},
    )
    lead = SimpleNamespace(stage=LeadStage.WON)
    db = MagicMock()
    db.scalars.return_value = _mock_scalar_result([sequence])
    db.get.return_value = lead

    result = run_nurturing_followup(db)

    assert result["skipped_won"] == 1
    assert sequence.completed is True
    assert sequence.diagnosis_data["stop_reason"] == "lead_won"


def test_objection_keyword_match_returns_rule_based_response(monkeypatch):
    monkeypatch.setattr("app.services.objection_service.settings.claude_api_key", "")
    objection = SimpleNamespace(
        id=uuid4(),
        gym_id=None,
        is_active=True,
        trigger_keywords=["caro", "preco"],
        response_template="O ROI compensa o investimento.",
    )
    db = MagicMock()
    db.scalars.return_value = _mock_scalar_result([objection])

    result = generate_objection_response(db, message_text="Achei caro pelo preco atual")

    assert result["matched"] is True
    assert result["objection_id"] == objection.id
    assert "ROI" in result["response_text"]
    assert result["source"] == "keyword_rule"


def test_objection_without_keyword_returns_generic(monkeypatch):
    monkeypatch.setattr("app.services.objection_service.settings.claude_api_key", "")
    db = MagicMock()
    db.scalars.return_value = _mock_scalar_result([])

    result = generate_objection_response(db, message_text="Tenho uma duvida geral")

    assert result["matched"] is False
    assert result["objection_id"] is None
    assert result["source"] == "generic"


def test_background_failure_records_diagnosis_error_and_audit(monkeypatch):
    lead_id = uuid4()
    public_gym_id = UUID("11111111-1111-1111-1111-111111111111")
    lead = SimpleNamespace(id=lead_id, notes=[])
    fake_db = MagicMock()
    fake_db.get.return_value = lead

    audit_calls = []

    monkeypatch.setattr("app.services.diagnosis_service.SessionLocal", lambda: fake_db)
    monkeypatch.setattr("app.services.diagnosis_service.resolve_public_gym_id", lambda: public_gym_id)
    monkeypatch.setattr("app.services.diagnosis_service.set_current_gym_id", lambda *_: None)
    monkeypatch.setattr("app.services.diagnosis_service.clear_current_gym_id", lambda: None)
    monkeypatch.setattr(
        "app.services.diagnosis_service.parse_diagnosis_checkins_csv",
        lambda *_: (_ for _ in ()).throw(ValueError("csv invalido")),
    )
    monkeypatch.setattr(
        "app.services.diagnosis_service.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    process_public_diagnosis_background(
        diagnosis_id=uuid4(),
        lead_id=lead_id,
        payload={
            "full_name": "Prospect",
            "email": "prospect@test.com",
            "whatsapp": "5511999999999",
            "gym_name": "Gym Test",
            "total_members": 100,
            "avg_monthly_fee": 199.0,
        },
        csv_content=b"nome,data\nAluno,\n",
        requester_ip="127.0.0.1",
        user_agent="pytest",
    )

    added_objects = [call.args[0] for call in fake_db.add.call_args_list]
    assert any(isinstance(obj, DiagnosisError) for obj in added_objects)
    assert audit_calls[0]["action"] == "public_diagnosis_failed"
    assert any(note["type"] == "public_diagnosis_failed" for note in lead.notes)


def test_background_success_creates_nurturing_sequence(monkeypatch):
    lead_id = uuid4()
    public_gym_id = UUID("11111111-1111-1111-1111-111111111111")
    lead = SimpleNamespace(id=lead_id, notes=[])
    fake_db = MagicMock()
    fake_db.get.return_value = lead
    sequence_calls = []

    monkeypatch.setattr("app.services.diagnosis_service.SessionLocal", lambda: fake_db)
    monkeypatch.setattr("app.services.diagnosis_service.resolve_public_gym_id", lambda: public_gym_id)
    monkeypatch.setattr("app.services.diagnosis_service.set_current_gym_id", lambda *_: None)
    monkeypatch.setattr("app.services.diagnosis_service.clear_current_gym_id", lambda: None)
    monkeypatch.setattr(
        "app.services.diagnosis_service.parse_diagnosis_checkins_csv",
        lambda *_: [
            {
                "member_key": "Aluno 1",
                "last_checkin_at": "2026-03-01T10:00:00+00:00",
                "days_since_last_checkin": 4,
                "recent_weekly_avg": 2.0,
                "previous_weekly_avg": 2.0,
                "frequency_drop_pct": 0.0,
                "risk_level": "green",
            }
        ],
    )
    monkeypatch.setattr("app.services.diagnosis_service.send_email_with_attachment", lambda **_: True)
    monkeypatch.setattr(
        "app.services.diagnosis_service.send_whatsapp_sync",
        lambda *_args, **_kwargs: SimpleNamespace(status="sent"),
    )
    monkeypatch.setattr(
        "app.services.diagnosis_service.create_nurturing_sequence",
        lambda *args, **kwargs: sequence_calls.append(kwargs),
    )
    monkeypatch.setattr("app.services.diagnosis_service.log_audit_event", lambda *_args, **_kwargs: None)

    process_public_diagnosis_background(
        diagnosis_id=uuid4(),
        lead_id=lead_id,
        payload={
            "full_name": "Prospect",
            "email": "prospect@test.com",
            "whatsapp": "5511999999999",
            "gym_name": "Gym Test",
            "total_members": 100,
            "avg_monthly_fee": 199.0,
        },
        csv_content=b"member_name,checkin_at\nAluno 1,2026-03-01 10:00\n",
        requester_ip="127.0.0.1",
        user_agent="pytest",
    )

    assert len(sequence_calls) == 1
    assert sequence_calls[0]["lead_id"] == lead_id
