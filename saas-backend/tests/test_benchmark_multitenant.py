"""
Test that assessment benchmark filters by gym_id (multi-tenant fix).
"""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.assessment_benchmark_service import build_benchmark

GYM_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
GYM_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_assessment(gym_id, member_id=None, strength=60, cardio=60):
    a = MagicMock()
    a.gym_id = gym_id
    a.member_id = member_id or uuid.uuid4()
    a.deleted_at = None
    a.extra_data = {"goal_type": "general"}
    a.strength_score = strength
    a.cardio_score = cardio
    return a


def _make_member(gym_id=GYM_A):
    m = MagicMock()
    m.gym_id = gym_id
    m.id = uuid.uuid4()
    return m


def test_benchmark_only_returns_same_gym_assessments():
    """build_benchmark must not include assessments from other gyms."""
    gym_a_assessment = _make_assessment(GYM_A)
    gym_b_assessment = _make_assessment(GYM_B)

    db = MagicMock()
    # Simulate DB returning only gym_a assessments when filtered by gym_id
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [gym_a_assessment]
    db.scalars.return_value = mock_scalars

    member = _make_member(GYM_A)
    result = build_benchmark(
        db,
        member,
        latest_assessment=gym_a_assessment,
        goal_type="general",
        overall_score=60,
        gym_id=GYM_A,
    )

    # Verify the query was called with gym_id filter (check call args)
    call_args = db.scalars.call_args
    assert call_args is not None
    # The statement passed to scalars should have gym_id in its whereclause
    stmt = call_args[0][0]
    stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    # UUID may be rendered with or without dashes depending on SQLAlchemy dialect
    gym_a_hex = str(GYM_A).replace("-", "")
    assert gym_a_hex in stmt_str or str(GYM_A) in stmt_str

    assert result["sample_size"] == 1


def test_benchmark_accepts_gym_id_parameter():
    """build_benchmark signature must include gym_id."""
    import inspect
    sig = inspect.signature(build_benchmark)
    assert "gym_id" in sig.parameters
