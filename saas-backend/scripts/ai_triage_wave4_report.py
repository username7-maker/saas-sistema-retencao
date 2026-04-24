from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

from sqlalchemy import select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import AITriageRecommendation, AuditLog, Gym
from app.services.ai_triage_service import get_ai_triage_metrics_summary, sync_ai_triage_recommendations


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Wave 4 pilot evidence report for the AI triage inbox.")
    parser.add_argument("--gym-slug", default="ai-gym-os-piloto")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()

    cutoff = _utcnow() - timedelta(hours=max(args.hours, 1))
    db = SessionLocal()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == args.gym_slug))
        if gym is None:
            raise SystemExit(f"Gym slug not found: {args.gym_slug}")
        set_current_gym_id(gym.id)

        sync_ai_triage_recommendations(db, gym_id=gym.id)
        db.commit()

        metrics = get_ai_triage_metrics_summary(db, gym_id=gym.id).model_dump()
        recommendations = list(
            db.scalars(
                select(AITriageRecommendation)
                .where(
                    AITriageRecommendation.gym_id == gym.id,
                    AITriageRecommendation.is_active.is_(True),
                )
                .order_by(AITriageRecommendation.priority_score.desc(), AITriageRecommendation.created_at.asc())
            ).all()
        )
        audit_rows = list(
            db.scalars(
                select(AuditLog)
                .where(
                    AuditLog.gym_id == gym.id,
                    AuditLog.entity == "ai_triage_recommendation",
                    AuditLog.created_at >= cutoff,
                )
                .order_by(AuditLog.created_at.asc())
            ).all()
        )

        events_by_recommendation = defaultdict(list)
        for event in audit_rows:
            key = str(event.entity_id) if event.entity_id else None
            if key:
                events_by_recommendation[key].append(event)

        same_day_touched = 0
        first_action_latencies_seconds: list[float] = []
        first_follow_up_latencies_seconds: list[float] = []
        actions_prepared_total = 0

        for recommendation in recommendations:
            rec_events = events_by_recommendation.get(str(recommendation.id), [])
            suggested_at = None
            prepared_at = None
            for event in rec_events:
                if event.action in {"ai_triage_recommendation_suggested", "ai_triage_recommendation_refreshed"} and suggested_at is None:
                    suggested_at = event.created_at
                if event.action == "ai_triage_action_prepared" and prepared_at is None:
                    prepared_at = event.created_at
                    actions_prepared_total += 1

            if suggested_at and prepared_at:
                latency = (prepared_at - suggested_at).total_seconds()
                first_action_latencies_seconds.append(latency)
                if suggested_at.date() == prepared_at.date():
                    same_day_touched += 1
                if recommendation.source_domain == "retention":
                    first_follow_up_latencies_seconds.append(latency)

        total_active = len(recommendations)
        touched_same_day_pct = round((same_day_touched / total_active) * 100, 2) if total_active else 0.0
        actions_per_operator_day = actions_prepared_total
        first_action_seconds = min(first_action_latencies_seconds) if first_action_latencies_seconds else None
        median_follow_up_seconds = median(first_follow_up_latencies_seconds) if first_follow_up_latencies_seconds else None

        payload = {
            "generated_at": _utcnow().isoformat(),
            "gym_slug": args.gym_slug,
            "window_hours": args.hours,
            "metrics_summary": metrics,
            "baseline_comparison": {
                "time_to_first_action_after_triage_seconds": first_action_seconds,
                "prioritized_touched_same_day_pct": touched_same_day_pct,
                "actions_executed_per_operator_day": actions_per_operator_day,
                "time_between_visible_risk_and_first_follow_up_seconds": median_follow_up_seconds,
            },
            "recommendations": [
                {
                    "id": str(item.id),
                    "subject_name": item.payload_snapshot.get("subject_name"),
                    "source_domain": item.source_domain,
                    "priority_score": item.priority_score,
                    "approval_state": item.approval_state,
                    "execution_state": item.execution_state,
                    "outcome_state": item.outcome_state,
                }
                for item in recommendations
            ],
        }

        md_lines = [
            "# 04.43 Wave 4 Pilot Walkthrough",
            "",
            f"- Scope: `{args.gym_slug}`",
            f"- Generated at: `{payload['generated_at']}`",
            f"- Active recommendations: `{total_active}`",
            f"- Approved: `{metrics['approved_total']}`",
            f"- Prepared actions: `{metrics['prepared_action_total']}`",
            f"- Acceptance rate: `{metrics['acceptance_rate']}`",
            "",
            "## Baseline Comparison",
            "",
            f"1. Tempo ate a primeira acao apos a triagem: `{first_action_seconds}` segundos",
            f"2. Percentual de itens prioritarios tocados no mesmo dia: `{touched_same_day_pct}%`",
            f"3. Acoes executadas/preparadas por operador no walkthrough: `{actions_per_operator_day}`",
            f"4. Tempo entre risco visivel e primeiro follow-up: `{median_follow_up_seconds}` segundos",
            "",
            "## Leitura",
            "",
            "- O baseline manual da `4.43` continua definido pelas quatro metricas congeladas em `04.43-BASELINE.md`.",
            "- Esta rodada entrega um walkthrough controlado no tenant do piloto, com aprovacao humana item por item e tool layer segura.",
            "- A comparacao e registrada como capability proof do primeiro loop AI-first, nao como serie historica longa do piloto.",
            "",
            "## Recommendations",
            "",
        ]
        for item in payload["recommendations"]:
            md_lines.append(
                f"- `{item['source_domain']}` | `{item['subject_name']}` | prioridade `{item['priority_score']}` | "
                f"`{item['approval_state']}` / `{item['execution_state']}` / `{item['outcome_state']}`"
            )

        json_path = Path(args.output_json)
        md_path = Path(args.output_md)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
