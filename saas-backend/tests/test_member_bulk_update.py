from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from app.models import MemberStatus, RiskLevel
from app.schemas.member import (
    MemberBulkUpdateChanges,
    MemberBulkUpdateCommitInput,
    MemberBulkUpdateFilters,
    MemberBulkUpdatePreviewInput,
)
from app.services.member_bulk_update_service import apply_member_bulk_update, preview_member_bulk_update


def make_member(
    *,
    member_id=None,
    full_name: str = "Aluno Teste",
    status: MemberStatus = MemberStatus.ACTIVE,
    plan_name: str = "Plano Base",
    monthly_fee: Decimal = Decimal("149.90"),
    preferred_shift: str | None = "manha",
    risk_score: int = 42,
):
    return SimpleNamespace(
        id=member_id or uuid4(),
        gym_id=uuid4(),
        full_name=full_name,
        email=f"{full_name.lower().replace(' ', '.')}@teste.com",
        deleted_at=None,
        status=status,
        plan_name=plan_name,
        monthly_fee=monthly_fee,
        preferred_shift=preferred_shift,
        risk_score=risk_score,
        risk_level=RiskLevel.YELLOW,
        updated_at=None,
    )


def _preview_payload(*, target_mode: str = "selected", selected_ids=None, status=MemberStatus.PAUSED):
    return MemberBulkUpdatePreviewInput(
        target_mode=target_mode,
        selected_member_ids=selected_ids or [uuid4()],
        filters=MemberBulkUpdateFilters(search="Ana"),
        changes=MemberBulkUpdateChanges(status=status),
    )


def test_preview_selected_members_counts_changed_and_unchanged():
    gym_id = uuid4()
    selected_id = uuid4()
    changed = make_member(member_id=selected_id, full_name="Ana", status=MemberStatus.ACTIVE)
    unchanged = make_member(member_id=uuid4(), full_name="Bruno", status=MemberStatus.PAUSED)

    db = MagicMock()
    db.scalars.return_value.all.return_value = [changed, unchanged]

    preview = preview_member_bulk_update(
        db,
        gym_id=gym_id,
        payload=_preview_payload(selected_ids=[selected_id, unchanged.id]),
    )

    assert preview.total_candidates == 2
    assert preview.would_update == 1
    assert preview.unchanged == 1
    assert preview.changed_fields == ["status"]
    assert preview.sample_members[0].full_name == "Ana"
    assert preview.sample_members[0].current_values["status"] == "active"
    assert preview.sample_members[0].next_values["status"] == "paused"


def test_preview_filtered_members_uses_member_filters():
    gym_id = uuid4()
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    preview_member_bulk_update(
        db,
        gym_id=gym_id,
        payload=MemberBulkUpdatePreviewInput(
            target_mode="filtered",
            selected_member_ids=[],
            filters=MemberBulkUpdateFilters(
                search="MAT-001",
                risk_level=RiskLevel.RED,
                status=MemberStatus.ACTIVE,
                plan_cycle="annual",
                min_days_without_checkin=14,
                provisional_only=True,
            ),
            changes=MemberBulkUpdateChanges(plan_name="Plano Premium"),
        ),
    )

    stmt = db.scalars.call_args.args[0]
    compiled = str(stmt)
    assert "members.gym_id" in compiled
    assert "risk_level" in compiled
    assert "last_checkin_at" in compiled
    assert "plan_name" in compiled


def test_commit_updates_only_members_with_effective_changes(monkeypatch):
    gym_id = uuid4()
    changed = make_member(full_name="Ana", status=MemberStatus.ACTIVE, plan_name="Plano Base")
    unchanged = make_member(full_name="Bruno", status=MemberStatus.PAUSED, plan_name="Plano Premium")

    db = MagicMock()
    db.scalars.return_value.all.return_value = [changed, unchanged]

    invalidated: list[tuple] = []
    monkeypatch.setattr(
        "app.services.member_bulk_update_service.invalidate_dashboard_cache",
        lambda *domains, **kwargs: invalidated.append((domains, kwargs)),
    )

    result = apply_member_bulk_update(
        db,
        gym_id=gym_id,
        payload=MemberBulkUpdateCommitInput(
            target_mode="selected",
            selected_member_ids=[changed.id, unchanged.id],
            filters=MemberBulkUpdateFilters(),
            changes=MemberBulkUpdateChanges(status=MemberStatus.PAUSED, plan_name="Plano Premium"),
        ),
    )

    assert result.updated == 1
    assert result.unchanged == 1
    assert changed.status == MemberStatus.PAUSED
    assert changed.plan_name == "Plano Premium"
    assert unchanged.status == MemberStatus.PAUSED
    assert unchanged.plan_name == "Plano Premium"
    assert db.add.call_count == 1
    assert invalidated == [(("members", "risk", "financial"), {"gym_id": gym_id})]


def test_commit_selected_raises_when_members_not_found():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        apply_member_bulk_update(
            db,
            gym_id=uuid4(),
            payload=MemberBulkUpdateCommitInput(
                target_mode="selected",
                selected_member_ids=[uuid4()],
                filters=MemberBulkUpdateFilters(),
                changes=MemberBulkUpdateChanges(preferred_shift="noite"),
            ),
        )

    assert exc_info.value.status_code == 404
