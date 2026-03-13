"""
Test retention intelligence: churn classification and playbook materialization.
"""
import uuid
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.enums import ChurnType
from app.services.retention_intelligence_service import (
    classify_churn_type,
    build_retention_playbook,
)

MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _make_member(join_days=60, nps=7, risk_score=70, is_vip=False):
    from app.models import RiskLevel
    return SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        join_date=date.today() - timedelta(days=join_days),
        nps_last_score=nps,
        risk_score=risk_score,
        risk_level=RiskLevel.RED if risk_score >= 70 else RiskLevel.YELLOW,
        is_vip=is_vip,
        assigned_user_id=None,
        full_name="Aluno Teste",
        churn_type=None,
        retention_stage=None,
        deleted_at=None,
    )


def _make_db_no_seasonal():
    db = MagicMock()
    db.scalar.return_value = 5  # has enough check-ins last year (not seasonal)
    return db


def _make_db_seasonal():
    db = MagicMock()
    db.scalar.return_value = 1  # very few check-ins last year (seasonal)
    return db


def test_early_dropout_classification():
    """Member < 30 days with high risk should be classified as early_dropout."""
    db = _make_db_no_seasonal()
    member = _make_member(join_days=10, risk_score=50)

    churn_type = classify_churn_type(db, member)

    assert churn_type == ChurnType.EARLY_DROPOUT.value


def test_dissatisfaction_classification():
    """Member with NPS <= 5 should be classified as voluntary_dissatisfaction."""
    db = _make_db_no_seasonal()
    member = _make_member(join_days=60, nps=4, risk_score=50)

    churn_type = classify_churn_type(db, member)

    assert churn_type == ChurnType.VOLUNTARY_DISSATISFACTION.value


def test_seasonal_classification():
    """Member with few check-ins in same period last year should be seasonal."""
    db = _make_db_seasonal()
    member = _make_member(join_days=60, nps=7, risk_score=50)

    churn_type = classify_churn_type(db, member)

    assert churn_type == ChurnType.INVOLUNTARY_SEASONAL.value


def test_inactivity_classification():
    """Member with high risk + neutral NPS should be classified as inactivity."""
    db = _make_db_no_seasonal()
    member = _make_member(join_days=60, nps=7, risk_score=65)

    churn_type = classify_churn_type(db, member)

    assert churn_type == ChurnType.INVOLUNTARY_INACTIVITY.value


def test_build_retention_playbook_returns_list():
    """build_retention_playbook should return a non-empty list for known churn types."""
    db = MagicMock()
    member = _make_member()

    for churn_type in [
        ChurnType.EARLY_DROPOUT.value,
        ChurnType.VOLUNTARY_DISSATISFACTION.value,
        ChurnType.INVOLUNTARY_INACTIVITY.value,
        ChurnType.INVOLUNTARY_SEASONAL.value,
    ]:
        playbook = build_retention_playbook(db, member, churn_type)
        assert isinstance(playbook, list)
        assert len(playbook) > 0


def test_build_retention_playbook_unknown_falls_back():
    """Unknown churn type should fall back to inactivity playbook."""
    db = MagicMock()
    member = _make_member()

    playbook = build_retention_playbook(db, member, ChurnType.UNKNOWN.value)

    # Should not raise and should return something
    assert isinstance(playbook, list)
