from sqlalchemy import select, update

from app.database import clear_current_gym_id, include_all_tenants, set_unscoped_access, unscoped_tenant_access
from app.models import User


def test_include_all_tenants_requires_reason():
    try:
        include_all_tenants(select(User), reason="")
    except ValueError as exc:
        assert "reason" in str(exc).lower()
    else:
        raise AssertionError("include_all_tenants should reject empty reason")


def test_include_all_tenants_records_reason_in_execution_options():
    statement = include_all_tenants(select(User), reason="dependencies.get_current_user")

    options = statement.get_execution_options()

    assert options["include_all_tenants"] is True
    assert options["tenant_bypass_reason"] == "dependencies.get_current_user"


def test_include_all_tenants_rejects_non_allowlisted_reason():
    try:
        include_all_tenants(select(User), reason="tests.database.guardrail")
    except ValueError as exc:
        assert "allowlisted" in str(exc).lower()
    else:
        raise AssertionError("include_all_tenants should reject ad hoc reasons")


def test_include_all_tenants_also_wraps_non_select_statements():
    statement = include_all_tenants(
        update(User).where(User.id == "00000000-0000-0000-0000-000000000000"),
        reason="auth.refresh_access_token",
    )

    options = statement.get_execution_options()

    assert options["include_all_tenants"] is True
    assert options["tenant_bypass_reason"] == "auth.refresh_access_token"


def test_include_all_tenants_emits_allowlisted_telemetry(caplog):
    clear_current_gym_id()

    with caplog.at_level("INFO", logger="app.database"):
        include_all_tenants(select(User), reason="dependencies.get_current_user")

    matching = [
        record
        for record in caplog.records
        if getattr(record, "extra_fields", {}).get("event") == "tenant_bypass_include_all_tenants"
    ]

    assert len(matching) == 1
    assert matching[0].extra_fields["status"] == "allowed"
    assert matching[0].extra_fields["tenant_bypass_reason"] == "dependencies.get_current_user"


def test_set_unscoped_access_requires_reason_when_enabled():
    try:
        set_unscoped_access(True)
    except ValueError as exc:
        assert "reason" in str(exc).lower()
    else:
        raise AssertionError("set_unscoped_access should reject empty reason")


def test_unscoped_tenant_access_rejects_non_allowlisted_reason():
    try:
        with unscoped_tenant_access("tests.database.unscoped"):
            pass
    except ValueError as exc:
        assert "allowlisted" in str(exc).lower()
    else:
        raise AssertionError("unscoped_tenant_access should reject ad hoc reasons")


def test_unscoped_tenant_access_context_restores_state():
    with unscoped_tenant_access("jobs.nurturing_followup_job"):
        pass

    set_unscoped_access(False)


def test_unscoped_tenant_access_emits_allowlisted_telemetry(caplog):
    clear_current_gym_id()

    with caplog.at_level("INFO", logger="app.database"):
        with unscoped_tenant_access("jobs.nurturing_followup_job"):
            pass

    matching = [
        record
        for record in caplog.records
        if getattr(record, "extra_fields", {}).get("event") == "tenant_bypass_unscoped_access"
    ]

    assert len(matching) == 1
    assert matching[0].extra_fields["status"] == "allowed"
    assert matching[0].extra_fields["tenant_bypass_reason"] == "jobs.nurturing_followup_job"
