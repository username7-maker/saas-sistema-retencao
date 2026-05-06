import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum
from app.schemas.common import PaginatedResponse
from app.schemas.coach import CoachWorkspaceOut, CoachWorkspaceSummaryOut
from app.schemas.work_queue import WorkQueueItemOut
from app.services.coach_workspace_service import get_coach_workspace


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _user(role=RoleEnum.TRAINER, *, work_shift="afternoon", work_shift_scope=None):
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        role=role,
        work_shift=work_shift,
        work_shift_scope=work_shift_scope,
    )


def _work_item(**kwargs):
    defaults = dict(
        source_type="task",
        source_id=uuid.uuid4(),
        subject_name="Aluno Tecnico",
        member_id=MEMBER_ID,
        lead_id=None,
        subject_phone=None,
        domain="trainer",
        severity="high",
        preferred_shift="afternoon",
        reason="Verificar se o treino foi entregue.",
        primary_action_label="Verificar treino",
        primary_action_type="open_context",
        suggested_message=None,
        requires_confirmation=False,
        state="do_now",
        due_at=datetime.now(tz=timezone.utc) - timedelta(hours=2),
        visible_from=None,
        assigned_to_user_id=None,
        context_path=f"/assessments/members/{MEMBER_ID}?tab=acoes",
        outcome_state="pending",
        technical_ladder_step="training_delivery_check_d8",
        technical_ladder_step_label="D+8 treino",
        autopilot_badges=[],
    )
    defaults.update(kwargs)
    return WorkQueueItemOut(**defaults)


def test_coach_workspace_uses_trainer_domain_and_maps_lanes(monkeypatch):
    captured = {}

    def fake_list_work_queue_items(*args, **kwargs):
        captured.update(kwargs)
        return PaginatedResponse(items=[_work_item()], total=1, page=1, page_size=25)

    monkeypatch.setattr("app.services.coach_workspace_service.list_work_queue_items", fake_list_work_queue_items)

    result = get_coach_workspace(MagicMock(), current_user=_user(), state="do_now", shift="my_shift")

    assert captured["domain"] == "trainer"
    assert captured["source"] == "all"
    assert captured["shift"] == "my_shift"
    assert result.total == 1
    assert result.items[0].lane == "training_delivery"
    assert result.items[0].next_action_label == "Verificar treino"
    assert "training_delivered" in result.items[0].allowed_outcomes
    assert result.summary.by_lane == {"training_delivery": 1}


def test_coach_workspace_downgrades_all_shift_for_trainer(monkeypatch):
    captured = {}

    def fake_list_work_queue_items(*args, **kwargs):
        captured.update(kwargs)
        return PaginatedResponse(items=[], total=0, page=1, page_size=25)

    monkeypatch.setattr("app.services.coach_workspace_service.list_work_queue_items", fake_list_work_queue_items)

    result = get_coach_workspace(MagicMock(), current_user=_user(), state="do_now", shift="all")

    assert captured["shift"] == "my_shift"
    assert result.shift == "my_shift"


def test_coach_workspace_all_shift_allowed_for_manager(monkeypatch):
    captured = {}

    def fake_list_work_queue_items(*args, **kwargs):
        captured.update(kwargs)
        return PaginatedResponse(
            items=[
                _work_item(
                    primary_action_label="Registrar feedback",
                    technical_ladder_step="training_feedback_d14",
                    technical_ladder_step_label="D+14 feedback",
                )
            ],
            total=1,
            page=1,
            page_size=25,
        )

    monkeypatch.setattr("app.services.coach_workspace_service.list_work_queue_items", fake_list_work_queue_items)

    result = get_coach_workspace(MagicMock(), current_user=_user(RoleEnum.MANAGER), state="do_now", shift="all")

    assert captured["shift"] == "all"
    assert result.shift == "all"
    assert result.items[0].lane == "training_feedback"


def test_coach_workspace_endpoint_returns_contract_for_trainer(app, client, monkeypatch):
    trainer = _user(RoleEnum.TRAINER, work_shift="evening", work_shift_scope=["evening", "overnight"])
    mock_db = MagicMock()
    calls = {}

    def fake_get_coach_workspace(db, *, current_user, state, shift, page, page_size):
        calls.update(
            {
                "db": db,
                "current_user": current_user,
                "state": state,
                "shift": shift,
                "page": page,
                "page_size": page_size,
            }
        )
        return CoachWorkspaceOut(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            state=state,
            shift=shift,
            summary=CoachWorkspaceSummaryOut(),
            generated_at=datetime.now(tz=timezone.utc),
        )

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: trainer
    monkeypatch.setattr("app.routers.coach.get_coach_workspace", fake_get_coach_workspace)

    try:
        response = client.get("/api/v1/coach/workspace?state=do_now&shift=my_shift&page=1&page_size=25")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert calls["current_user"].role == RoleEnum.TRAINER
    assert calls["shift"] == "my_shift"
    assert calls["state"] == "do_now"


def test_coach_workspace_endpoint_blocks_receptionist(app, client):
    receptionist = _user(RoleEnum.RECEPTIONIST, work_shift="morning")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: receptionist

    try:
        response = client.get("/api/v1/coach/workspace")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
