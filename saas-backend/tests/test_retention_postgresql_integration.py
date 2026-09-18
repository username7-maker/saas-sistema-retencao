"""Real locking/rollback checks. Run with RETENTION_TEST_DATABASE_URL pointing to a local *_test DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import get_current_gym_id, set_current_gym_id
from app.models import AuditLog, Gym, Member, RiskAlert, RiskLevel, User
from app.models.enums import RoleEnum as UserRole
from app.models.base import Base
from app.services import dashboard_service


@pytest.fixture
def pg_queue():
    raw_url = os.environ.get("RETENTION_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set RETENTION_TEST_DATABASE_URL to run isolated PostgreSQL integration tests")
    url = make_url(raw_url)
    if url.host not in {"127.0.0.1", "localhost"} or not (url.database or "").endswith("_test"):
        pytest.fail("Integration tests require a local database with a name ending in _test")
    admin = create_engine(url)
    schema = "retention_test_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"})
    previous_gym = get_current_gym_id()
    gym_id, user_id, other_gym = uuid4(), uuid4(), uuid4()
    try:
        Base.metadata.create_all(engine)
        # Core inserts seed only synthetic records; application code uses normal tenant-scoped sessions.
        with engine.begin() as connection:
            for identifier in [gym_id, other_gym]:
                connection.execute(Gym.__table__.insert().values(id=identifier, name="Synthetic test gym", slug=str(identifier)))
            connection.execute(User.__table__.insert().values(id=user_id, gym_id=gym_id, full_name="Test owner",
                email="owner@example.test", hashed_password="not-a-real-password", role=UserRole.OWNER))
            for tenant in [gym_id, other_gym]:
                for index in range(2):
                    member_id = uuid4()
                    connection.execute(Member.__table__.insert().values(id=member_id, gym_id=tenant,
                        full_name=f"Synthetic {index}", risk_level=RiskLevel.RED, risk_score=85,
                        last_checkin_at=datetime.now(timezone.utc) - timedelta(days=20)))
                    connection.execute(RiskAlert.__table__.insert().values(id=uuid4(), gym_id=tenant,
                        member_id=member_id, score=85, level=RiskLevel.RED))
        set_current_gym_id(gym_id)
        yield engine, SimpleNamespace(id=user_id, gym_id=gym_id, role=UserRole.OWNER), other_gym
    finally:
        set_current_gym_id(previous_gym)
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_bulk_resolution_persists_audit_and_respects_tenant(pg_queue, monkeypatch):
    engine, owner, other_gym = pg_queue
    monkeypatch.setattr(dashboard_service, "invalidate_dashboard_cache", lambda *args, **kwargs: None)
    with Session(engine) as db:
        result = dashboard_service.resolve_retention_queue(db, current_user=owner, expected_count=2)
    assert result.resolved_count == 2
    with Session(engine) as db:
        alerts = db.scalars(select(RiskAlert)).all()
        assert len(alerts) == 2
        assert all(a.resolved and a.resolved_by_user_id == owner.id and a.resolved_at for a in alerts)
        assert all(a.episode_key and a.automation_stage and len(a.action_history) == 1 for a in alerts)
        actions = [entry.action for entry in db.scalars(select(AuditLog)).all()]
        assert actions.count("risk_alert_resolved") == 2
        assert actions.count("retention_queue_bulk_resolved") == 1
    with engine.connect() as connection:
        assert not any(connection.execute(select(RiskAlert.__table__.c.resolved).where(RiskAlert.__table__.c.gym_id == other_gym)).scalars())


def test_failure_rolls_back_flushed_rows_and_audit_in_postgresql(pg_queue, monkeypatch):
    engine, owner, _ = pg_queue
    original = dashboard_service._apply_risk_alert_resolution
    calls = 0
    def fail_after_first_flush(db, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("controlled failure")
        result = original(db, **kwargs)
        db.flush()
        return result
    monkeypatch.setattr(dashboard_service, "_apply_risk_alert_resolution", fail_after_first_flush)
    with Session(engine) as db, pytest.raises(RuntimeError, match="controlled failure"):
        dashboard_service.resolve_retention_queue(db, current_user=owner, expected_count=2)
    with Session(engine) as db:
        assert all(not a.resolved and not a.action_history for a in db.scalars(select(RiskAlert)).all())
        assert db.scalars(select(AuditLog)).all() == []


def test_concurrent_batches_resolve_once_and_require_reconfirmation(pg_queue, monkeypatch):
    engine, owner, _ = pg_queue
    locked, release = Event(), Event()
    original = dashboard_service._apply_risk_alert_resolution
    def hold_lock(db, **kwargs):
        locked.set()
        assert release.wait(10), "Test failed to release the first transaction"
        return original(db, **kwargs)
    monkeypatch.setattr(dashboard_service, "_apply_risk_alert_resolution", hold_lock)
    monkeypatch.setattr(dashboard_service, "invalidate_dashboard_cache", lambda *args, **kwargs: None)
    def resolve():
        set_current_gym_id(owner.gym_id)
        with Session(engine) as db:
            try:
                return dashboard_service.resolve_retention_queue(db, current_user=owner, expected_count=2).resolved_count
            except HTTPException as error:
                db.rollback()
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(resolve)
        try:
            assert locked.wait(5)
            second = pool.submit(resolve)
            deadline = monotonic() + 4
            waiting = False
            with engine.connect() as connection:
                while monotonic() < deadline and not waiting:
                    waiting = bool(connection.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'")))
                    connection.commit()
                    if not waiting:
                        sleep(.05)
            assert waiting, "Second batch must wait for the first transaction's row lock"
        finally:
            release.set()
        assert first.result(timeout=5) == 2
        assert second.result(timeout=5) == 409
    with Session(engine) as db:
        assert all(len(a.action_history) == 1 for a in db.scalars(select(RiskAlert)).all())
