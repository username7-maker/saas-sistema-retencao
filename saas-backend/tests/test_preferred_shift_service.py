from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.preferred_shift_service import (
    PREFERRED_SHIFT_LOOKBACK_DAYS,
    build_preferred_shift_diagnostic,
    checkin_shift_case,
    derive_preferred_shift_from_counts,
    normalize_preferred_shift,
    sync_preferred_shifts_from_checkins,
)


def test_normalize_preferred_shift_supports_aliases() -> None:
    assert normalize_preferred_shift("Madrugada") == "overnight"
    assert normalize_preferred_shift("plantao_madrugada") == "overnight"
    assert normalize_preferred_shift("Manha") == "morning"
    assert normalize_preferred_shift("vespertino") == "afternoon"
    assert normalize_preferred_shift("noturno") == "evening"
    assert normalize_preferred_shift("LIVRE, LIVRE") is None


def test_derive_preferred_shift_requires_clear_pattern() -> None:
    assert PREFERRED_SHIFT_LOOKBACK_DAYS == 30
    assert derive_preferred_shift_from_counts({"overnight": 3, "morning": 1, "afternoon": 0, "evening": 0}) == "overnight"
    assert derive_preferred_shift_from_counts({"morning": 2, "afternoon": 0, "evening": 0}) == "morning"
    assert derive_preferred_shift_from_counts({"morning": 2, "afternoon": 1, "evening": 0}) == "morning"
    assert derive_preferred_shift_from_counts({"morning": 1, "afternoon": 1, "evening": 0}) is None
    assert derive_preferred_shift_from_counts({"morning": 1, "afternoon": 0, "evening": 0}) == "morning"
    assert derive_preferred_shift_from_counts({"morning": 1, "afternoon": 2, "evening": 0}) == "afternoon"


def test_build_preferred_shift_diagnostic_explains_no_recent_checkins() -> None:
    diagnostic = build_preferred_shift_diagnostic({})

    assert diagnostic["status"] == "no_recent_checkins"
    assert diagnostic["reason"] == "Sem check-in recente/importado nos ultimos 30 dias."
    assert diagnostic["counts"]["morning"] == 0


def test_build_preferred_shift_diagnostic_explains_tie() -> None:
    diagnostic = build_preferred_shift_diagnostic({"morning": 1, "afternoon": 1})

    assert diagnostic["status"] == "tie"
    assert diagnostic["reason"] == "Empate nos ultimos 30 dias: Manha 1, Tarde 1"
    assert diagnostic["counts"]["morning"] == 1
    assert diagnostic["counts"]["afternoon"] == 1


def test_checkin_shift_case_uses_overnight_bucket() -> None:
    compiled = str(checkin_shift_case().compile(compile_kwargs={"literal_binds": True}))
    assert "hour_bucket < 6" in compiled
    assert "'overnight'" in compiled


@patch("app.services.preferred_shift_service.invalidate_dashboard_cache")
def test_sync_preferred_shifts_updates_member_from_recent_checkins(mock_cache) -> None:
    member_id = uuid4()
    member = SimpleNamespace(id=member_id, preferred_shift=None, deleted_at=None)
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = [
        SimpleNamespace(member_id=member_id, shift_key="morning", total=4),
        SimpleNamespace(member_id=member_id, shift_key="afternoon", total=1),
    ]

    updated = sync_preferred_shifts_from_checkins(db, member_ids={member_id}, commit=False)

    assert updated == 1
    assert member.preferred_shift == "morning"
    db.add.assert_called_once_with(member)
    db.flush.assert_called_once()
    db.commit.assert_not_called()
    mock_cache.assert_called_once_with("members")


@patch("app.services.preferred_shift_service.invalidate_dashboard_cache")
def test_sync_preferred_shifts_clears_noisy_legacy_values(mock_cache) -> None:
    member_id = uuid4()
    member = SimpleNamespace(id=member_id, preferred_shift="LIVRE, LIVRE", deleted_at=None)
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    updated = sync_preferred_shifts_from_checkins(db, member_ids={member_id}, commit=False)

    assert updated == 1
    assert member.preferred_shift is None
    db.add.assert_called_once_with(member)
    db.flush.assert_called_once()
    mock_cache.assert_called_once_with("members")


@patch("app.services.preferred_shift_service.invalidate_dashboard_cache")
def test_sync_preferred_shifts_clears_existing_shift_when_recent_checkins_tie(mock_cache) -> None:
    member_id = uuid4()
    member = SimpleNamespace(id=member_id, preferred_shift="afternoon", deleted_at=None)
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = [
        SimpleNamespace(member_id=member_id, shift_key="afternoon", total=1),
        SimpleNamespace(member_id=member_id, shift_key="morning", total=1),
    ]

    updated = sync_preferred_shifts_from_checkins(db, member_ids={member_id}, commit=False)

    assert updated == 1
    assert member.preferred_shift is None
    db.add.assert_called_once_with(member)
    db.flush.assert_called_once()
    mock_cache.assert_called_once_with("members")


@patch("app.services.preferred_shift_service.invalidate_dashboard_cache")
def test_sync_preferred_shifts_keeps_canonical_manual_value_without_signal(mock_cache) -> None:
    member_id = uuid4()
    member = SimpleNamespace(id=member_id, preferred_shift="morning", deleted_at=None)
    db = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [member]
    db.scalars.return_value = mock_scalars
    db.execute.return_value.all.return_value = []

    updated = sync_preferred_shifts_from_checkins(db, member_ids={member_id}, commit=False)

    assert updated == 0
    assert member.preferred_shift == "morning"
    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()
    mock_cache.assert_not_called()
