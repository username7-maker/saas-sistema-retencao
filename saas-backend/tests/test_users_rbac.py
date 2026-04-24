import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import RoleEnum
from app.routers.users import create_user_endpoint
from app.schemas import UserRegister


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NEW_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


def _request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={"user-agent": "pytest"})


def _current_user(role: RoleEnum):
    return SimpleNamespace(id=USER_ID, gym_id=GYM_ID, role=role)


def _payload(role: RoleEnum):
    return UserRegister(
        full_name="Novo Usuario",
        email="novo@example.com",
        password="Secret123!",
        role=role,
    )


def test_manager_cannot_create_owner() -> None:
    with pytest.raises(HTTPException) as exc_info:
        create_user_endpoint(
            _request(),
            _payload(RoleEnum.OWNER),
            MagicMock(),
            _current_user(RoleEnum.MANAGER),
        )

    assert exc_info.value.status_code == 403


@patch("app.routers.users.log_audit_event")
@patch("app.routers.users.create_user")
def test_manager_can_create_trainer(mock_create_user, mock_log_audit) -> None:
    db = MagicMock()
    created = SimpleNamespace(
        id=NEW_USER_ID,
        gym_id=GYM_ID,
        full_name="Instrutor",
        email="trainer@example.com",
        role=RoleEnum.TRAINER,
        is_active=True,
        created_at=None,
    )
    mock_create_user.return_value = created

    result = create_user_endpoint(
        _request(),
        _payload(RoleEnum.TRAINER),
        db,
        _current_user(RoleEnum.MANAGER),
    )

    assert result is created
    db.commit.assert_called_once()
    mock_log_audit.assert_called_once()
