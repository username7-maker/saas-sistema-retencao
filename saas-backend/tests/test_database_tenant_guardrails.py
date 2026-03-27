from sqlalchemy import select

from app.database import include_all_tenants, set_unscoped_access, unscoped_tenant_access
from app.models import User


def test_include_all_tenants_requires_reason():
    try:
        include_all_tenants(select(User), reason="")
    except ValueError as exc:
        assert "reason" in str(exc).lower()
    else:
        raise AssertionError("include_all_tenants should reject empty reason")


def test_include_all_tenants_records_reason_in_execution_options():
    statement = include_all_tenants(select(User), reason="tests.database.guardrail")

    options = statement.get_execution_options()

    assert options["include_all_tenants"] is True
    assert options["tenant_bypass_reason"] == "tests.database.guardrail"


def test_set_unscoped_access_requires_reason_when_enabled():
    try:
        set_unscoped_access(True)
    except ValueError as exc:
        assert "reason" in str(exc).lower()
    else:
        raise AssertionError("set_unscoped_access should reject empty reason")


def test_unscoped_tenant_access_context_restores_state():
    with unscoped_tenant_access("tests.database.unscoped"):
        pass

    set_unscoped_access(False)
