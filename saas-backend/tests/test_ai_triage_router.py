from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.routers.ai_triage import (
    get_ai_triage_item,
    get_ai_triage_metrics_summary_endpoint,
    list_ai_triage_items,
    prepare_ai_triage_item_action,
    update_ai_triage_item_approval,
    update_ai_triage_item_outcome,
)


def test_list_ai_triage_items_syncs_and_returns_paginated_payload(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    captured: dict[str, object] = {}

    def _sync(_db, *, gym_id, limit_per_domain=50):
        captured["gym_id"] = gym_id
        captured["limit_per_domain"] = limit_per_domain
        return []

    monkeypatch.setattr("app.routers.ai_triage.sync_ai_triage_recommendations", _sync)
    monkeypatch.setattr(
        "app.routers.ai_triage.list_ai_triage_recommendations",
        lambda *_args, **kwargs: SimpleNamespace(items=[], total=0, page=kwargs["page"], page_size=kwargs["page_size"]),
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.routers.ai_triage.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = list_ai_triage_items(request=request, db=db, current_user=current_user, page=2, page_size=15)

    assert captured == {"gym_id": current_user.gym_id, "limit_per_domain": 50}
    assert response.page == 2
    assert response.page_size == 15
    assert audit_calls[0]["action"] == "ai_triage_list_viewed"
    db.commit.assert_called_once()


def test_get_ai_triage_item_logs_detail_view(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    recommendation_id = uuid4()
    recommendation = SimpleNamespace(
        id=recommendation_id,
        gym_id=current_user.gym_id,
        member_id=uuid4(),
        source_domain="retention",
        source_entity_kind="member",
        source_entity_id=uuid4(),
    )

    monkeypatch.setattr("app.routers.ai_triage.sync_ai_triage_recommendations", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "app.routers.ai_triage.get_ai_triage_recommendation_or_404",
        lambda *_args, **_kwargs: recommendation,
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.serialize_ai_triage_recommendation",
        lambda rec: SimpleNamespace(id=rec.id, source_domain=rec.source_domain),
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr("app.routers.ai_triage.log_audit_event", lambda *_args, **kwargs: audit_calls.append(kwargs))

    response = get_ai_triage_item(
        recommendation_id=recommendation_id,
        request=request,
        db=db,
        current_user=current_user,
    )

    assert response.id == recommendation_id
    assert audit_calls[0]["action"] == "ai_triage_detail_viewed"
    assert audit_calls[0]["entity_id"] == recommendation_id
    db.commit.assert_called_once()


def test_update_ai_triage_item_approval_commits(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    recommendation_id = uuid4()
    payload = SimpleNamespace(decision="approved", note="Pode seguir")

    monkeypatch.setattr(
        "app.routers.ai_triage.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.update_ai_triage_recommendation_approval",
        lambda *_args, **kwargs: SimpleNamespace(id=kwargs["recommendation_id"], approval_state=kwargs["decision"]),
    )

    response = update_ai_triage_item_approval(
        recommendation_id=recommendation_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
    )

    assert response.id == recommendation_id
    assert response.approval_state == "approved"
    db.commit.assert_called_once()


def test_get_ai_triage_metrics_summary_endpoint_commits(monkeypatch):
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    monkeypatch.setattr("app.routers.ai_triage.sync_ai_triage_recommendations", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        "app.routers.ai_triage.get_ai_triage_metrics_summary",
        lambda *_args, **_kwargs: SimpleNamespace(total_active=1),
    )

    response = get_ai_triage_metrics_summary_endpoint(db=db, current_user=current_user)

    assert response.total_active == 1
    db.commit.assert_called_once()


def test_prepare_ai_triage_item_action_commits(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    recommendation_id = uuid4()
    payload = SimpleNamespace(
        action="create_task",
        assigned_to_user_id=None,
        owner_role=None,
        owner_label=None,
        note="Criar task",
        operator_note="Pode seguir",
        auto_approve=True,
        confirm_approval=False,
    )

    monkeypatch.setattr(
        "app.routers.ai_triage.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.prepare_ai_triage_recommendation_action",
        lambda *_args, **kwargs: SimpleNamespace(
            action=kwargs["action"],
            supported=True,
            detail="ok",
            recommendation=SimpleNamespace(id=kwargs["recommendation_id"]),
        ),
    )

    response = prepare_ai_triage_item_action(
        recommendation_id=recommendation_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
    )

    assert response.action == "create_task"
    assert response.supported is True
    db.commit.assert_called_once()


def test_update_ai_triage_item_outcome_commits(monkeypatch):
    request = MagicMock()
    db = MagicMock()
    current_user = SimpleNamespace(id=uuid4(), gym_id=uuid4())
    recommendation_id = uuid4()
    payload = SimpleNamespace(outcome="positive", note="Contato feito")

    monkeypatch.setattr(
        "app.routers.ai_triage.get_request_context",
        lambda *_args, **_kwargs: {"ip_address": "127.0.0.1", "user_agent": "pytest"},
    )
    monkeypatch.setattr(
        "app.routers.ai_triage.update_ai_triage_recommendation_outcome",
        lambda *_args, **kwargs: SimpleNamespace(id=kwargs["recommendation_id"], outcome_state=kwargs["outcome"]),
    )

    response = update_ai_triage_item_outcome(
        recommendation_id=recommendation_id,
        payload=payload,
        request=request,
        db=db,
        current_user=current_user,
    )

    assert response.id == recommendation_id
    assert response.outcome_state == "positive"
    db.commit.assert_called_once()
