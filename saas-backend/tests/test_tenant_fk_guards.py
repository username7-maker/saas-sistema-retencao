import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas import LeadCreate, MemberCreate, TaskCreate


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
