import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.database import SessionLocal
from app.models.core_async_job import CoreAsyncJob
from app.models.gym import Gym
from app.services.core_async_job_service import (
    enqueue_whatsapp_webhook_setup_job,
    get_core_async_job,
    process_pending_core_async_jobs,
    serialize_core_async_job,
)
from app.services.evolution_service import ensure_instance


def _percentile_cont(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def main() -> None:
    parser = argparse.ArgumentParser(description="Create controlled production samples for CoreAsyncJob queue wait.")
    parser.add_argument("--gym-slug", required=True, help="Pilot gym slug.")
    parser.add_argument("--repeats", type=int, default=5, help="How many sequential samples to generate.")
    parser.add_argument(
        "--allow-ensure-instance",
        action="store_true",
        help="If the gym has no whatsapp_instance persisted, create/reuse the deterministic Evolution instance without mutating Gym state.",
    )
    args = parser.parse_args()

    if not settings.public_backend_url or not settings.whatsapp_webhook_token:
        raise SystemExit("PUBLIC_BACKEND_URL ou WHATSAPP_WEBHOOK_TOKEN ausente.")

    webhook_url = f"{settings.public_backend_url.rstrip('/')}/api/v1/whatsapp/webhook"
    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug))
        if gym is None:
            raise SystemExit(f"Gym slug nao encontrada: {args.gym_slug}")
        instance = gym.whatsapp_instance
        if not instance:
            if not args.allow_ensure_instance:
                raise SystemExit(f"Gym {args.gym_slug} nao possui whatsapp_instance ativa; smoke abortado.")
            instance = ensure_instance(str(gym.id))

        runs: list[dict] = []
        for index in range(max(args.repeats, 1)):
            job, created = enqueue_whatsapp_webhook_setup_job(
                db,
                gym_id=gym.id,
                requested_by_user_id=None,
                instance=instance,
                webhook_url=webhook_url,
                webhook_headers={"X-Webhook-Token": settings.whatsapp_webhook_token},
            )
            db.commit()
            if created:
                process_pending_core_async_jobs(batch_size=1)
            status_db = SessionLocal()
            try:
                refreshed = status_db.scalar(select(CoreAsyncJob).where(CoreAsyncJob.id == job.id, CoreAsyncJob.gym_id == gym.id))
                if refreshed is None:
                    raise SystemExit(f"Job {job.id} nao encontrado apos processamento.")
                serialized = serialize_core_async_job(refreshed)
            finally:
                status_db.close()
            runs.append(
                {
                    "iteration": index + 1,
                    "created_new_job": created,
                    "job": {
                        "job_id": str(serialized["job_id"]),
                        "status": serialized["status"],
                        "attempt_count": serialized["attempt_count"],
                        "queue_wait_seconds": serialized["queue_wait_seconds"],
                        "started_at": serialized["started_at"].isoformat() if serialized["started_at"] else None,
                        "completed_at": serialized["completed_at"].isoformat() if serialized["completed_at"] else None,
                        "error_code": serialized["error_code"],
                    },
                }
            )

        queue_waits = [float(item["job"]["queue_wait_seconds"]) for item in runs if item["job"]["queue_wait_seconds"] is not None]
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gym_slug": args.gym_slug,
            "job_type": "whatsapp_webhook_setup",
            "repeats": len(runs),
            "instance": instance,
            "used_persisted_instance": bool(gym.whatsapp_instance),
            "webhook_url": webhook_url,
            "samples": runs,
            "aggregate": {
                "sample_count": len(queue_waits),
                "p50_queue_wait_seconds": _percentile_cont(queue_waits, 0.5),
                "p95_queue_wait_seconds": _percentile_cont(queue_waits, 0.95),
                "max_queue_wait_seconds": max(queue_waits) if queue_waits else None,
                "under_budget": bool(queue_waits) and (_percentile_cont(queue_waits, 0.95) or 0) < 60,
            },
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
