"""Coverage evidence for daily check-in files, stored with the import audit."""
import json
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from app.database import get_current_gym_id
from app.models import AuditLog


def pending_dates(anchor: date | None, completed: set[date], incoming: set[date]) -> list[str]:
    if not incoming:
        return []
    start = min(anchor, min(incoming)) if anchor else min(incoming)
    end = max(incoming)
    if (end - start).days > 3660:
        raise ValueError("Periodo de acessos excede 10 anos; confira as datas do arquivo.")
    known = completed | incoming
    return [(start + timedelta(days=i)).isoformat() for i in range((end-start).days + 1)
            if start + timedelta(days=i) not in known]


def coverage_preview(db, incoming: set[date], latest_legacy: datetime | None):
    gym_id = get_current_gym_id()
    completed: set[date] = set()
    anchors: list[date] = []
    baseline = None
    # Explicit scope in addition to the session tenant guard.
    rows = db.execute(select(AuditLog.details).where(
        AuditLog.gym_id == gym_id, AuditLog.action == "import_checkins_csv",
        AuditLog.details["daily_coverage"].astext.is_not(None),
    )).all() if gym_id else []
    for (details,) in rows:
        if not isinstance(details, dict):
            continue
        coverage = details.get("daily_coverage")
        if not isinstance(coverage, dict):
            continue
        try:
            if coverage.get("start"):
                anchors.append(date.fromisoformat(coverage["start"]))
            if coverage.get("baseline"):
                baseline = date.fromisoformat(coverage["baseline"])
                completed.add(baseline)
            completed.update(date.fromisoformat(value) for value in coverage.get("completed_dates", []))
        except (TypeError, ValueError):
            continue
    if anchors:
        anchor = min(anchors)
    elif isinstance(latest_legacy, datetime):
        # Preserve the established import date convention; do not shift legacy timestamps.
        anchor = latest_legacy.date()
        completed.add(anchor)
        baseline = anchor
    else:
        anchor = min(incoming) if incoming else None
    return anchor.isoformat() if anchor else None, pending_dates(anchor, completed, incoming), baseline.isoformat() if baseline else None


def require_coverage_acknowledgement(pending: list[str], acknowledged: str | None):
    if not pending:
        return
    try:
        values = json.loads(acknowledged or "null")
    except (ValueError, TypeError):
        values = None
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or set(values) != set(pending):
        raise HTTPException(status_code=409, detail={
            "code": "pending_import_days", "pending_dates": pending,
            "message": "Ha dias anteriores sem importacao completa. Revalide o arquivo e confirme as datas pendentes antes de continuar.",
        })
