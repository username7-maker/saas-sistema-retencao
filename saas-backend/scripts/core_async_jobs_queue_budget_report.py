import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, text


CRITICAL_JOB_TYPES = (
    "public_diagnosis",
    "lead_proposal_dispatch",
    "nps_dispatch",
    "monthly_reports_dispatch",
    "whatsapp_webhook_setup",
)
CRITICAL_JOB_TYPES_SQL = ", ".join(f"'{job_type}'" for job_type in CRITICAL_JOB_TYPES)


@dataclass
class QueueBudgetRow:
    job_type: str
    total_jobs: int
    p50_seconds: float | None
    p95_seconds: float | None
    max_seconds: float | None
    over_budget_jobs: int


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL nao encontrada no ambiente.")
    return database_url


def _round_metric(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _fetch_rows(*, connection, cutoff: datetime, gym_slug: str | None) -> tuple[dict[str, Any], list[QueueBudgetRow]]:
    params = {"cutoff": cutoff, "gym_slug": gym_slug}
    filter_sql = f"""
        from core_async_jobs j
        join gyms g on g.id = j.gym_id
        where j.created_at >= :cutoff
          and j.started_at is not null
          and j.job_type in ({CRITICAL_JOB_TYPES_SQL})
          and (:gym_slug is null or g.slug = :gym_slug)
    """
    overall_sql = text(
        f"""
        select
            count(*) as total_jobs,
            percentile_cont(0.5) within group (order by extract(epoch from (j.started_at - j.created_at))) as p50_seconds,
            percentile_cont(0.95) within group (order by extract(epoch from (j.started_at - j.created_at))) as p95_seconds,
            max(extract(epoch from (j.started_at - j.created_at))) as max_seconds,
            sum(case when extract(epoch from (j.started_at - j.created_at)) > 60 then 1 else 0 end) as over_budget_jobs
        {filter_sql}
        """
    )
    by_job_sql = text(
        f"""
        select
            j.job_type,
            count(*) as total_jobs,
            percentile_cont(0.5) within group (order by extract(epoch from (j.started_at - j.created_at))) as p50_seconds,
            percentile_cont(0.95) within group (order by extract(epoch from (j.started_at - j.created_at))) as p95_seconds,
            max(extract(epoch from (j.started_at - j.created_at))) as max_seconds,
            sum(case when extract(epoch from (j.started_at - j.created_at)) > 60 then 1 else 0 end) as over_budget_jobs
        {filter_sql}
        group by j.job_type
        order by j.job_type
        """
    )

    overall = dict(connection.execute(overall_sql, params).mappings().one())
    rows = [
        QueueBudgetRow(
            job_type=str(row["job_type"]),
            total_jobs=int(row["total_jobs"] or 0),
            p50_seconds=_round_metric(row["p50_seconds"]),
            p95_seconds=_round_metric(row["p95_seconds"]),
            max_seconds=_round_metric(row["max_seconds"]),
            over_budget_jobs=int(row["over_budget_jobs"] or 0),
        )
        for row in connection.execute(by_job_sql, params).mappings().all()
    ]
    return overall, rows


def _json_payload(*, cutoff: datetime, gym_slug: str | None, overall: dict[str, Any], rows: list[QueueBudgetRow]) -> dict[str, Any]:
    total_jobs = int(overall.get("total_jobs") or 0)
    p95_seconds = _round_metric(overall.get("p95_seconds"))
    return {
        "window_days": int((datetime.now(timezone.utc) - cutoff).days),
        "window_started_at": cutoff.isoformat(),
        "window_ended_at": datetime.now(timezone.utc).isoformat(),
        "gym_slug": gym_slug,
        "critical_job_types": list(CRITICAL_JOB_TYPES),
        "overall": {
            "total_jobs": total_jobs,
            "p50_seconds": _round_metric(overall.get("p50_seconds")),
            "p95_seconds": p95_seconds,
            "max_seconds": _round_metric(overall.get("max_seconds")),
            "over_budget_jobs": int(overall.get("over_budget_jobs") or 0),
            "budget_target_seconds": 60,
            "budget_passed": total_jobs > 0 and p95_seconds is not None and p95_seconds < 60,
        },
        "by_job_type": [asdict(row) for row in rows],
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    overall = payload["overall"]
    scope_label = payload["gym_slug"] or "all-tenants"
    lines = [
        "# Core Async Jobs Queue Budget Report",
        "",
        f"- Scope: `{scope_label}`",
        f"- Window started at: `{payload['window_started_at']}`",
        f"- Window ended at: `{payload['window_ended_at']}`",
        f"- Budget target: `p95 < {overall['budget_target_seconds']}s`",
        "",
        "## Overall",
        "",
        "| total_jobs | p50_seconds | p95_seconds | max_seconds | over_budget_jobs | budget_passed |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {overall['total_jobs']} | {overall['p50_seconds']} | {overall['p95_seconds']} | {overall['max_seconds']} | {overall['over_budget_jobs']} | {overall['budget_passed']} |",
        "",
        "## By Job Type",
        "",
        "| job_type | total_jobs | p50_seconds | p95_seconds | max_seconds | over_budget_jobs |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["by_job_type"]:
        lines.append(
            f"| {row['job_type']} | {row['total_jobs']} | {row['p50_seconds']} | {row['p95_seconds']} | {row['max_seconds']} | {row['over_budget_jobs']} |"
        )
    if not payload["by_job_type"]:
        lines.append("| no-data | 0 | - | - | - | - |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure p95 queue wait for durable core async jobs.")
    parser.add_argument("--days", type=int, default=14, help="Rolling window size in days.")
    parser.add_argument("--gym-slug", default="", help="Optional gym slug to scope the report.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(args.days, 1))
    gym_slug = args.gym_slug.strip() or None
    engine = create_engine(_require_database_url(), future=True)

    with engine.connect() as connection:
        overall, rows = _fetch_rows(connection=connection, cutoff=cutoff, gym_slug=gym_slug)

    payload = _json_payload(cutoff=cutoff, gym_slug=gym_slug, overall=overall, rows=rows)
    if args.format == "markdown":
        print(_render_markdown(payload))
        return

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
