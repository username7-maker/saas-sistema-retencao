from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from app.services.kommo_service import _normalize_member_salesbot_domain, _resolve_member_salesbot_route


GYM_ID = UUID("11111111-1111-1111-1111-111111111111")
TRAINER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _route(**overrides):
    payload = {
        "is_enabled": True,
        "pipeline_id": "100",
        "stage_id": "200",
        "salesbot_id": "300",
        "message_field_id": "400",
        "pdf_url_field_id": None,
        "pdf_delivery_mode": "native_file_required",
        "channel_source_id": None,
        "responsible_user_id": None,
        "tags": [],
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_trainer_alias_normalizes_to_assessment_domain():
    assert _normalize_member_salesbot_domain("trainer") == "assessment"


def test_resolver_uses_trainer_route_for_technical_domain():
    domain_route = _route(pipeline_id="10")
    trainer_route = _route(pipeline_id="20")
    db = MagicMock()
    db.scalar.side_effect = [domain_route, trainer_route]
    member = SimpleNamespace(assigned_user_id=TRAINER_ID)

    resolved = _resolve_member_salesbot_route(db, gym_id=GYM_ID, member=member, domain="assessment", pdf_url=None)

    assert resolved.route is trainer_route
    assert resolved.route_kind == "trainer_route"
    assert resolved.trainer_user_id == TRAINER_ID


def test_resolver_falls_back_to_coordination_when_member_has_no_trainer():
    domain_route = _route(pipeline_id="10")
    db = MagicMock()
    db.scalar.side_effect = [domain_route]
    member = SimpleNamespace(assigned_user_id=None)

    resolved = _resolve_member_salesbot_route(db, gym_id=GYM_ID, member=member, domain="body_composition", pdf_url=None)

    assert resolved.route is domain_route
    assert resolved.route_kind == "coordination_fallback"
    assert resolved.fallback_reason == "no_assigned_trainer"


def test_resolver_falls_back_when_trainer_route_is_incomplete():
    domain_route = _route(pipeline_id="10")
    trainer_route = _route(message_field_id=None)
    db = MagicMock()
    db.scalar.side_effect = [domain_route, trainer_route]
    member = SimpleNamespace(assigned_user_id=TRAINER_ID)

    resolved = _resolve_member_salesbot_route(db, gym_id=GYM_ID, member=member, domain="student_ai", pdf_url=None)

    assert resolved.route is domain_route
    assert resolved.route_kind == "coordination_fallback"
    assert resolved.trainer_user_id == TRAINER_ID
    assert resolved.fallback_reason == "trainer_route_incomplete"


def test_resolver_keeps_non_technical_domain_on_domain_route():
    domain_route = _route(pipeline_id="10")
    db = MagicMock()
    db.scalar.side_effect = [domain_route]
    member = SimpleNamespace(assigned_user_id=TRAINER_ID)

    resolved = _resolve_member_salesbot_route(db, gym_id=GYM_ID, member=member, domain="retention", pdf_url=None)

    assert resolved.route is domain_route
    assert resolved.route_kind == "domain_route"
    assert resolved.trainer_user_id is None
