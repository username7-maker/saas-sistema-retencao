import logging
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_current_gym_id


logger = logging.getLogger(__name__)


def refresh_member_kpis_materialized_view(db: Session) -> bool:
    if not _is_postgres(db):
        return False

    try:
        db.execute(text("REFRESH MATERIALIZED VIEW mv_monthly_member_kpis"))
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Falha ao atualizar materialized view mv_monthly_member_kpis")
        return False


def get_monthly_member_kpis(db: Session, months: int) -> dict[str, dict[str, Any]]:
    gym_id = get_current_gym_id()
    if not gym_id or months < 1 or not _is_postgres(db):
        return {}

    start_month = _subtract_months(date.today().replace(day=1), months - 1)
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    to_char(month_start, 'YYYY-MM') AS month_label,
                    total_mrr,
                    cancelled_members,
                    active_members
                FROM mv_monthly_member_kpis
                WHERE gym_id = :gym_id
                  AND month_start >= :start_month
                ORDER BY month_start
                """
            ),
            {"gym_id": str(gym_id), "start_month": start_month},
        ).mappings().all()
    except SQLAlchemyError:
        logger.exception("Falha ao consultar materialized view mv_monthly_member_kpis")
        return {}

    data: dict[str, dict[str, Any]] = {}
    for row in rows:
        month = str(row.get("month_label"))
        mrr_raw = row.get("total_mrr") or Decimal("0")
        data[month] = {
            "mrr": float(mrr_raw),
            "cancelled": int(row.get("cancelled_members") or 0),
            "active": int(row.get("active_members") or 0),
        }
    return data


def _is_postgres(db: Session) -> bool:
    bind = db.get_bind()
    if not bind:
        return False
    return bind.dialect.name == "postgresql"


def _subtract_months(base_date: date, months: int) -> date:
    year = base_date.year
    month = base_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)
