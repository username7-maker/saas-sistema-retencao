"""
Shared fixtures for the AI Gym OS test suite.

Strategy: models use postgresql.UUID so we mock DB sessions rather than
creating a full in-memory DB, keeping tests fast and dependency-free.
"""
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# App client (health endpoints do NOT require a DB session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Return the FastAPI app with scheduler disabled."""
    import os
    os.environ.setdefault("ENABLE_SCHEDULER", "false")
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    """TestClient for the FastAPI app."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared domain objects
# ---------------------------------------------------------------------------

GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def gym_id():
    return GYM_ID


@pytest.fixture
def user_id():
    return USER_ID


@pytest.fixture
def member_id():
    return MEMBER_ID


@pytest.fixture
def mock_gym():
    return SimpleNamespace(
        id=GYM_ID,
        name="Academia Teste",
        slug="academia-teste",
        is_active=True,
    )


@pytest.fixture
def mock_owner(mock_gym):
    from app.models import RoleEnum
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        full_name="Owner Teste",
        email="owner@teste.com",
        role=RoleEnum.OWNER,
        is_active=True,
        deleted_at=None,
        hashed_password="$2b$12$fakehash",
        gym=mock_gym,
    )


@pytest.fixture
def mock_member():
    from app.models import MemberStatus, RiskLevel
    return SimpleNamespace(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Aluno Teste",
        email="aluno@teste.com",
        phone="11999999999",
        status=MemberStatus.ACTIVE,
        risk_level=RiskLevel.GREEN,
        risk_score=0,
        join_date=datetime.now(tz=timezone.utc).date(),
        last_checkin_at=None,
        nps_last_score=None,
        loyalty_months=0,
        assigned_user_id=USER_ID,
        deleted_at=None,
    )


# ---------------------------------------------------------------------------
# Mock DB session factory
# ---------------------------------------------------------------------------

_UNSET = object()


def make_mock_db(scalar_returns=_UNSET, scalars_returns=None, execute_returns=None):
    """Return a MagicMock Session with pre-configured return values."""
    db = MagicMock()
    if scalar_returns is not _UNSET:
        values = scalar_returns if isinstance(scalar_returns, list) else [scalar_returns]
        db.scalar.side_effect = values
    if scalars_returns is not None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = scalars_returns
        db.scalars.return_value = mock_scalars
    if execute_returns is not None:
        db.execute.return_value = execute_returns
    return db
