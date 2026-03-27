import logging
import socket
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, case, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.distributed_lock import with_distributed_lock
from app.database import SessionLocal, clear_current_gym_id, include_all_tenants, set_current_gym_id
from app.models.risk_recalculation_request import RiskRecalculationRequest
from app.services.risk import run_daily_risk_processing

logger = logging.getLogger(__name__)

_STALE_LOCK_AFTER = timedelta(minutes=15)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _worker_id() -> str:
    return f"{socket.gethostname()}:{settings.app_name}:risk-recalc"


def serialize_risk_recalculation_request(request: RiskRecalculationRequest) -> dict:
    return {
        "request_id": request.id,
        "status": request.status,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "started_at": request.started_at,
        "completed_at": request.completed_at,
        "error_message": request.error_message,
        "result": request.result_json,
    }


def enqueue_risk_recalculation_request(
    db: Session,
    *,
    gym_id: UUID,
    requested_by_user_id: UUID | None,
) -> tuple[RiskRecalculationRequest, bool]:
    existing = db.scalar(
        select(RiskRecalculationRequest)
        .where(
            RiskRecalculationRequest.gym_id == gym_id,
            RiskRecalculationRequest.status.in_(("pending", "processing")),
        )
        .order_by(RiskRecalculationRequest.created_at.asc())
        .limit(1)
    )
    if existing:
        return existing, False

    request = RiskRecalculationRequest(
        gym_id=gym_id,
        requested_by_user_id=requested_by_user_id,
        status="pending",
    )
    db.add(request)
    db.flush()
    return request, True


def get_risk_recalculation_request(
    db: Session,
    *,
    request_id: UUID,
    gym_id: UUID,
) -> RiskRecalculationRequest | None:
    return db.scalar(
        select(RiskRecalculationRequest).where(
            RiskRecalculationRequest.id == request_id,
            RiskRecalculationRequest.gym_id == gym_id,
        )
    )


def _claim_next_request(db: Session, *, worker_id: str) -> RiskRecalculationRequest | None:
    now = _utcnow()
    stale_before = now - _STALE_LOCK_AFTER
    request = db.scalar(
        include_all_tenants(
            select(RiskRecalculationRequest)
            .where(
                or_(
                    RiskRecalculationRequest.status == "pending",
                    and_(
                        RiskRecalculationRequest.status == "processing",
                        RiskRecalculationRequest.locked_at.is_not(None),
                        RiskRecalculationRequest.locked_at < stale_before,
                    ),
                )
            )
            .order_by(
                case((RiskRecalculationRequest.status == "pending", 0), else_=1),
                RiskRecalculationRequest.created_at.asc(),
            )
            .limit(1),
            reason="risk_recalculation.claim_next_request",
        )
    )
    if request is None:
        return None

    request.status = "processing"
    request.started_at = request.started_at or now
    request.completed_at = None
    request.locked_at = now
    request.locked_by = worker_id
    request.error_message = None
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def _mark_request_pending(db: Session, request: RiskRecalculationRequest) -> None:
    request.status = "pending"
    request.locked_at = None
    request.locked_by = None
    db.add(request)
    db.commit()


def _mark_request_completed(db: Session, request: RiskRecalculationRequest, *, result: dict) -> None:
    request.status = "completed"
    request.completed_at = _utcnow()
    request.locked_at = None
    request.locked_by = None
    request.error_message = None
    request.result_json = result
    db.add(request)
    db.commit()


def _mark_request_failed(db: Session, request: RiskRecalculationRequest, *, error_message: str) -> None:
    request.status = "failed"
    request.completed_at = _utcnow()
    request.locked_at = None
    request.locked_by = None
    request.error_message = error_message
    db.add(request)
    db.commit()


def process_pending_risk_recalculation_requests(*, batch_size: int = 3) -> int:
    processed_count = 0
    worker_id = _worker_id()

    while processed_count < batch_size:
        db = SessionLocal()
        request: RiskRecalculationRequest | None = None
        try:
            request = _claim_next_request(db, worker_id=worker_id)
            if request is None:
                break

            set_current_gym_id(request.gym_id)

            @with_distributed_lock(
                "daily_risk",
                ttl_seconds=1800,
                fail_open=lambda: settings.scheduler_critical_lock_fail_open,
            )
            def _run_locked() -> dict[str, int] | None:
                return run_daily_risk_processing(db)

            result = _run_locked()
            if result is None:
                _mark_request_pending(db, request)
                break

            _mark_request_completed(db, request, result=result)
            processed_count += 1
            logger.info(
                "Risk recalculation request completed.",
                extra={
                    "extra_fields": {
                        "event": "risk_recalculation_request_completed",
                        "request_id": str(request.id),
                        "gym_id": str(request.gym_id),
                        "status": "completed",
                    }
                },
            )
        except Exception as exc:
            logger.exception(
                "Risk recalculation request failed.",
                extra={
                    "extra_fields": {
                        "event": "risk_recalculation_request_failed",
                        "request_id": str(request.id) if request else None,
                    }
                },
            )
            db.rollback()
            if request is not None:
                _mark_request_failed(db, request, error_message=str(exc))
        finally:
            clear_current_gym_id()
            db.close()

    return processed_count
