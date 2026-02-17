from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models import MemberStatus, RiskLevel, TaskStatus
from app.models.automation_rule import AutomationAction, AutomationTrigger
from app.services import automation_engine


class DummyDB:
    def __init__(self) -> None:
        self.added: list = []
        self.flushed = False
        self.committed = False
        self.values: list = []

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True

    def scalar(self, _query):
        if not self.values:
            return None
        return self.values.pop(0)

    def scalars(self, _query):
        return self

    def all(self):
        return self.values.pop(0) if self.values else []

    def get(self, model_class, rule_id):
        for obj in self.added:
            if hasattr(obj, "id") and obj.id == rule_id:
                return obj
        return None


def _make_member(
    *,
    phone: str | None = "11999999999",
    email: str | None = "test@test.com",
    risk_level: str = "red",
    risk_score: int = 80,
    last_checkin_days_ago: int = 14,
    nps_last_score: int = 5,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="member-1",
        full_name="Aluno Teste",
        phone=phone,
        email=email,
        plan_name="Plano Gold",
        risk_level=risk_level,
        risk_score=risk_score,
        nps_last_score=nps_last_score,
        assigned_user_id="user-1",
        last_checkin_at=datetime.now(tz=timezone.utc) - timedelta(days=last_checkin_days_ago),
        status=MemberStatus.ACTIVE,
        deleted_at=None,
    )


def _make_rule(
    *,
    trigger_type: str = AutomationTrigger.RISK_LEVEL_CHANGE,
    trigger_config: dict | None = None,
    action_type: str = AutomationAction.CREATE_TASK,
    action_config: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id="rule-1",
        name="Test Rule",
        trigger_type=trigger_type,
        trigger_config=trigger_config or {"level": "red"},
        action_type=action_type,
        action_config=action_config or {"title": "Contatar {nome}", "priority": "high"},
        is_active=True,
        executions_count=0,
        last_executed_at=None,
    )


def test_build_template_vars_includes_member_data():
    member = _make_member()
    vars_ = automation_engine._build_template_vars(member)

    assert vars_["nome"] == "Aluno Teste"
    assert vars_["plano"] == "Plano Gold"
    assert vars_["score"] == "80"
    assert vars_["nps"] == "5"
    assert int(vars_["dias"]) >= 14


def test_build_template_vars_handles_no_checkin():
    member = _make_member()
    member.last_checkin_at = None
    vars_ = automation_engine._build_template_vars(member)

    assert vars_["dias"] == "0"


def test_execute_rule_create_task_skips_when_no_existing(monkeypatch):
    db = DummyDB()
    db.values = [None]  # no existing task
    member = _make_member()
    rule = _make_rule(
        action_type=AutomationAction.CREATE_TASK,
        action_config={"title": "Contatar {nome}", "priority": "high"},
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "created"
    assert result["action"] == AutomationAction.CREATE_TASK


def test_execute_rule_create_task_skips_duplicate(monkeypatch):
    db = DummyDB()
    existing_task = SimpleNamespace(id="task-existing")
    db.values = [existing_task]  # task already exists
    member = _make_member()
    rule = _make_rule(
        action_type=AutomationAction.CREATE_TASK,
        action_config={"title": "Contatar {nome}", "priority": "high"},
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "skipped"
    assert result["reason"] == "task_already_exists"


def test_execute_rule_send_whatsapp_skips_no_phone(monkeypatch):
    db = DummyDB()
    member = _make_member(phone=None)
    rule = _make_rule(
        action_type=AutomationAction.SEND_WHATSAPP,
        action_config={"template": "risk_red"},
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "skipped"
    assert result["reason"] == "no_phone"


def test_execute_rule_send_email_skips_no_email(monkeypatch):
    db = DummyDB()
    member = _make_member(email=None)
    rule = _make_rule(
        action_type=AutomationAction.SEND_EMAIL,
        action_config={"subject": "Teste", "body": "Ola {nome}"},
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "skipped"
    assert result["reason"] == "no_email"


def test_execute_rule_send_email_calls_send(monkeypatch):
    db = DummyDB()
    member = _make_member()
    rule = _make_rule(
        action_type=AutomationAction.SEND_EMAIL,
        action_config={"subject": "Teste", "body": "Ola {nome}, volte!"},
    )

    sent_emails = []
    monkeypatch.setattr(
        automation_engine,
        "send_email",
        lambda to, subject, body: (sent_emails.append({"to": to, "subject": subject, "body": body}), True)[1],
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "sent"
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "test@test.com"
    assert "Aluno Teste" in sent_emails[0]["body"]


def test_execute_rule_notify_creates_notification(monkeypatch):
    db = DummyDB()
    member = _make_member()
    rule = _make_rule(
        action_type=AutomationAction.NOTIFY,
        action_config={"title": "Alerta: {nome}", "message": "{nome} precisa de atencao"},
    )

    notifications = []
    monkeypatch.setattr(
        automation_engine,
        "create_notification",
        lambda db_, **kwargs: (
            notifications.append(kwargs),
            SimpleNamespace(id="notif-1"),
        )[1],
    )

    result = automation_engine.execute_rule_for_member(db, rule, member)

    assert result["status"] == "notified"
    assert len(notifications) == 1
    assert "Aluno Teste" in notifications[0]["title"]


def test_seed_default_rules_creates_when_empty():
    db = DummyDB()
    db.values = [0]  # 0 existing rules

    rules = automation_engine.seed_default_rules(db)

    assert len(rules) == 5
    assert db.flushed is True


def test_seed_default_rules_skips_when_rules_exist():
    db = DummyDB()
    db.values = [3]  # 3 existing rules

    rules = automation_engine.seed_default_rules(db)

    assert len(rules) == 0
