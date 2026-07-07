import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas import LeadCreate, MemberCreate, TaskCreate
from app.schemas.method_os import HumanActionCreate, OperationalEventCreate, OutcomeCreate


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
LEAD_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


def test_member_create_rejects_cross_tenant_assignee() -> None:
    payload = MemberCreate(full_name="Aluno", assigned_user_id=USER_ID)
    db = MagicMock()
    db.scalar.return_value = None

    with patch("app.services.member_service.ensure_optional_user_in_gym") as mock_guard:
        mock_guard.side_effect = HTTPException(status_code=404, detail="Usuario nao encontrado")
        from app.services.member_service import create_member

        with pytest.raises(HTTPException) as exc_info:
            create_member(db, payload, gym_id=GYM_ID)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()


def test_task_create_rejects_cross_tenant_member() -> None:
    payload = TaskCreate(title="Ligar aluno", member_id=MEMBER_ID)
    db = MagicMock()

    with patch("app.services.task_service.ensure_optional_member_in_gym") as mock_guard:
        mock_guard.side_effect = HTTPException(status_code=404, detail="Membro nao encontrado")
        from app.services.task_service import create_task

        with pytest.raises(HTTPException) as exc_info:
            create_task(db, payload, gym_id=GYM_ID)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()


def test_lead_create_rejects_cross_tenant_owner() -> None:
    payload = LeadCreate(full_name="Lead", source="instagram", owner_id=USER_ID)
    db = MagicMock()

    with patch("app.services.crm_service.ensure_optional_user_in_gym") as mock_guard:
        mock_guard.side_effect = HTTPException(status_code=404, detail="Usuario nao encontrado")
        from app.services.crm_service import create_lead

        with pytest.raises(HTTPException) as exc_info:
            create_lead(db, payload, gym_id=GYM_ID)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()


def test_method_event_create_rejects_cross_tenant_person() -> None:
    from app.models import RoleEnum
    from app.services.method_os_service import create_event

    payload = OperationalEventCreate(person_id=MEMBER_ID, pillar="sales", event_type="proposal_no_response")
    current_user = SimpleNamespace(gym_id=GYM_ID, role=RoleEnum.OWNER)
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        create_event(db, current_user=current_user, payload=payload)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()


def test_method_action_create_rejects_cross_tenant_task() -> None:
    from app.models import RoleEnum
    from app.services.method_os_service import create_human_action

    payload = HumanActionCreate(action_type="whatsapp", action_summary="Contato feito", result="responded")
    current_user = SimpleNamespace(gym_id=GYM_ID, role=RoleEnum.OWNER, id=USER_ID, full_name="Owner", email="owner@test.com")
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        create_human_action(db, current_user=current_user, task_id=LEAD_ID, payload=payload)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()


def test_method_outcome_create_rejects_cross_tenant_task_link() -> None:
    from app.models import RoleEnum
    from app.services.method_os_service import create_outcome

    payload = OutcomeCreate(task_id=LEAD_ID, outcome_type="closed_sale")
    current_user = SimpleNamespace(gym_id=GYM_ID, role=RoleEnum.OWNER)
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        create_outcome(db, current_user=current_user, payload=payload)

    assert exc_info.value.status_code == 404
    db.add.assert_not_called()
