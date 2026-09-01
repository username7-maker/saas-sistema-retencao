from datetime import UTC, datetime
from uuid import uuid4

from app.services.database_storage_audit_service import (
    DatabaseStorageAudit,
    TableStorageStat,
    cleanup_policies,
)


def test_cleanup_policies_keep_business_records_out_of_scope() -> None:
    policies = cleanup_policies(datetime(2026, 9, 1, tzinfo=UTC))
    tables = {policy.table for policy in policies}

    assert "members" not in tables
    assert "assessments" not in tables
    assert "body_composition_evaluations" not in tables
    assert "financial_entries" not in tables
    assert "member_consent_records" not in tables
    assert "audit_logs" not in tables


def test_method_os_candidates_require_explicit_module_retirement() -> None:
    policies = cleanup_policies(datetime(2026, 9, 1, tzinfo=UTC))
    method_policies = [policy for policy in policies if policy.table.startswith("method_")]

    assert len(method_policies) == 8
    assert all(policy.requires_module_retirement for policy in method_policies)


def test_audit_digest_is_deterministic_and_declares_read_only_mode() -> None:
    gym_id = uuid4()
    audit = DatabaseStorageAudit(
        gym_id=gym_id,
        generated_at=datetime(2026, 9, 1, tzinfo=UTC),
        tables=(
            TableStorageStat(
                table="core_async_jobs",
                total_bytes=1024,
                table_bytes=768,
                index_bytes=256,
                live_rows_estimate=10,
                dead_rows_estimate=2,
            ),
        ),
        candidates=(),
    )

    assert audit.digest() == audit.digest()
    assert audit.as_dict()["mode"] == "read_only"
    assert audit.as_dict()["database_changed"] is False

