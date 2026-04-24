from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.services import core_async_job_service, risk_recalculation_service


def test_get_public_diagnosis_job_filters_by_gym_and_lead():
    diagnosis_id = uuid4()
    lead_id = uuid4()
    gym_id = uuid4()
    db = MagicMock()
    db.scalar.return_value = SimpleNamespace(id=diagnosis_id)

    result = core_async_job_service.get_public_diagnosis_job(
        db,
        diagnosis_id=diagnosis_id,
        lead_id=lead_id,
        gym_id=gym_id,
    )

    stmt = db.scalar.call_args.args[0]
    where_sql = [str(criteria) for criteria in stmt._where_criteria]

    assert result.id == diagnosis_id
    assert any("core_async_jobs.id" in criteria for criteria in where_sql)
    assert any("core_async_jobs.gym_id" in criteria for criteria in where_sql)
    assert any("core_async_jobs.related_entity_id" in criteria for criteria in where_sql)


def test_claim_next_core_async_job_uses_allowlisted_cross_tenant_reason():
    db = MagicMock()
    db.scalar.return_value = None

    result = core_async_job_service._claim_next_job(db, worker_id="worker-1")

    stmt = db.scalar.call_args.args[0]
    options = stmt.get_execution_options()

    assert result is None
    assert options["include_all_tenants"] is True
    assert options["tenant_bypass_reason"] == "core_async_jobs.claim_next_job"


def test_process_pending_core_async_jobs_sets_tenant_context_per_claimed_job():
    db_first = MagicMock()
    db_second = MagicMock()
    job = SimpleNamespace(id=uuid4(), gym_id=uuid4(), job_type="nps_dispatch")

    with (
        patch("app.services.core_async_job_service.SessionLocal", side_effect=[db_first, db_second]),
        patch("app.services.core_async_job_service._claim_next_job", side_effect=[job, None]) as claim_next_job,
        patch("app.services.core_async_job_service._dispatch_core_async_job", return_value={"processed": 1}) as dispatch_job,
        patch("app.services.core_async_job_service._mark_job_completed") as mark_completed,
        patch("app.services.core_async_job_service.set_current_gym_id") as set_current_gym_id,
        patch("app.services.core_async_job_service.clear_current_gym_id") as clear_current_gym_id,
    ):
        processed = core_async_job_service.process_pending_core_async_jobs(batch_size=5)

    assert processed == 1
    claim_next_job.assert_any_call(db_first, worker_id=claim_next_job.call_args_list[0].kwargs["worker_id"])
    dispatch_job.assert_called_once_with(db_first, job)
    mark_completed.assert_called_once_with(db_first, job, result={"processed": 1})
    set_current_gym_id.assert_called_once_with(job.gym_id)
    assert clear_current_gym_id.call_count == 2
    db_first.close.assert_called_once()
    db_second.close.assert_called_once()


def test_claim_next_risk_recalculation_request_uses_allowlisted_cross_tenant_reason():
    db = MagicMock()
    db.scalar.return_value = None

    result = risk_recalculation_service._claim_next_request(db, worker_id="worker-1")

    stmt = db.scalar.call_args.args[0]
    options = stmt.get_execution_options()

    assert result is None
    assert options["include_all_tenants"] is True
    assert options["tenant_bypass_reason"] == "risk_recalculation.claim_next_request"


def test_process_pending_risk_recalculation_requests_sets_tenant_context_per_request():
    db_first = MagicMock()
    db_second = MagicMock()
    request = SimpleNamespace(id=uuid4(), gym_id=uuid4())

    with (
        patch("app.services.risk_recalculation_service.SessionLocal", side_effect=[db_first, db_second]),
        patch("app.services.risk_recalculation_service._claim_next_request", side_effect=[request, None]),
        patch("app.services.risk_recalculation_service.with_distributed_lock", side_effect=lambda *args, **kwargs: (lambda fn: fn)),
        patch("app.services.risk_recalculation_service.run_daily_risk_processing", return_value={"processed": 2}),
        patch("app.services.risk_recalculation_service._mark_request_completed") as mark_completed,
        patch("app.services.risk_recalculation_service.set_current_gym_id") as set_current_gym_id,
        patch("app.services.risk_recalculation_service.clear_current_gym_id") as clear_current_gym_id,
    ):
        processed = risk_recalculation_service.process_pending_risk_recalculation_requests(batch_size=5)

    assert processed == 1
    set_current_gym_id.assert_called_once_with(request.gym_id)
    mark_completed.assert_called_once_with(db_first, request, result={"processed": 2})
    assert clear_current_gym_id.call_count == 2
    db_first.close.assert_called_once()
    db_second.close.assert_called_once()


def test_serialize_core_async_job_includes_queue_wait_seconds():
    created_at = datetime.now(timezone.utc) - timedelta(seconds=42)
    started_at = created_at + timedelta(seconds=17)
    job = SimpleNamespace(
        id=uuid4(),
        job_type="nps_dispatch",
        status="processing",
        attempt_count=1,
        max_attempts=5,
        next_retry_at=None,
        started_at=started_at,
        completed_at=None,
        error_code=None,
        error_message_redacted=None,
        result_json=None,
        related_entity_type="gym",
        related_entity_id=uuid4(),
        created_at=created_at,
    )

    serialized = core_async_job_service.serialize_core_async_job(job)

    assert serialized["queue_wait_seconds"] == 17
