from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.dependencies import get_current_user
from tests.conftest import GYM_ID, USER_ID


def test_get_current_user_reads_user_with_unscoped_query():
    user = SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        is_active=True,
        deleted_at=None,
    )
    db = MagicMock()
    db.scalar.return_value = user

    with patch(
        "app.core.dependencies.decode_token",
        return_value={"type": "access", "sub": str(USER_ID), "gym_id": str(GYM_ID)},
    ), patch("app.core.dependencies.set_current_gym_id") as set_gym_id:
        result = get_current_user(db, "valid-token")

    assert result is user
    db.scalar.assert_called_once()
    statement = db.scalar.call_args.args[0]
    assert statement.get_execution_options()["include_all_tenants"] is True
    assert statement.get_execution_options()["tenant_bypass_reason"] == "dependencies.get_current_user"
    set_gym_id.assert_called_once_with(GYM_ID)
