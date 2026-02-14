import pytest
from fastapi import HTTPException

from app.core.dependencies import require_roles
from app.models import RoleEnum


class DummyUser:
    def __init__(self, role: RoleEnum) -> None:
        self.role = role


def test_require_roles_allows_expected_role():
    dependency = require_roles(RoleEnum.OWNER, RoleEnum.MANAGER)
    user = DummyUser(RoleEnum.MANAGER)
    returned = dependency(user)  # type: ignore[arg-type]
    assert returned.role == RoleEnum.MANAGER


def test_require_roles_blocks_invalid_role():
    dependency = require_roles(RoleEnum.OWNER, RoleEnum.MANAGER)
    user = DummyUser(RoleEnum.RECEPTIONIST)
    with pytest.raises(HTTPException) as exc_info:
        dependency(user)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 403
