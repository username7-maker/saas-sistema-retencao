from datetime import date, datetime, time, timedelta, timezone
import os
import random

from sqlalchemy import func, select

from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.core.cache import invalidate_dashboard_cache
from app.models import (
    AuditLog,
    AutomationRule,
    Checkin,
    CheckinSource,
    Goal,
    Gym,
    InAppNotification,
    Lead,
    LeadStage,
    Member,
    MemberStatus,
    MessageLog,
    NPSResponse,
    NPSSentiment,
    NPSTrigger,
    RiskAlert,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.services.analytics_view_service import refresh_member_kpis_materialized_view
from app.services.automation_engine import run_automation_rules

TAG = os.getenv("SEED_TAG", "SEED100_EDGE_V2")
SLUG = os.getenv("SEED_GYM_SLUG", "academia-local")
RND = random.Random(int(os.getenv("SEED_RANDOM", "20260304")))


def sentiment(score: int) -> NPSSentiment:
    if score >= 9:
        return NPSSentiment.POSITIVE
    if score >= 7:
        return NPSSentiment.NEUTRAL
    return NPSSentiment.NEGATIVE


def pick(items, n: int):
    if not items:
        return []
    n = min(len(items), n)
    return RND.sample(items, k=n)

def main() -> None:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    today = date.today()
    try:
        gym = db.scalar(select(Gym).where(Gym.slug == SLUG, Gym.is_active.is_(True)))
        if not gym:
            raise RuntimeError(f"Academia '{SLUG}' nao encontrada")

        set_current_gym_id(gym.id)

        members = list(db.scalars(select(Member).where(Member.gym_id == gym.id, Member.full_name.like(f"[{TAG}]%"), Member.deleted_at.is_(None))).all())
        if not members:
            raise RuntimeError(f"Nenhum membro da tag {TAG} encontrado. Rode o seed base com essa tag primeiro.")

        users = list(db.scalars(select(User).where(User.gym_id == gym.id, User.deleted_at.is_(None), User.is_active.is_(True))).all())

        active = [m for m in members if m.status == MemberStatus.ACTIVE]
        paused = [m for m in members if m.status == MemberStatus.PAUSED]
        cancelled = [m for m in members if m.status == MemberStatus.CANCELLED]

        for m in pick(active, 12):
            m.email = None
            db.add(m)
        for m in pick(active, 12):
            m.phone = None
            db.add(m)

        # Force birthday trigger candidates
        today_birth = today.replace(year=max(1980, today.year - 30)).isoformat()
        for m in pick(members, 20):
            extra = dict(m.extra_data or {})
            extra["date_of_birth"] = today_birth
            extra["edge_tag"] = TAG
            m.extra_data = extra
            db.add(m)

        for m in pick(active, 10):
            m.last_checkin_at = None
            m.risk_level = RiskLevel.RED
            m.risk_score = max(85, m.risk_score)
            db.add(m)

        for m in pick(paused, 10):
            m.risk_level = RiskLevel.YELLOW
            m.risk_score = max(55, min(75, m.risk_score))
            db.add(m)

        for m in pick(cancelled, 8):
            if not m.cancellation_date:
                m.cancellation_date = today - timedelta(days=RND.randint(5, 120))
            db.add(m)

        # Make check-in streak members (7 distinct recent days)
        streak_members = pick(active, 8)
        for m in streak_members:
            for d in range(0, 7):
                dt = (now - timedelta(days=d)).replace(hour=RND.randint(7, 21), minute=0, second=0, microsecond=0)
                exists = db.scalar(select(Checkin.id).where(Checkin.member_id == m.id, Checkin.checkin_at == dt))
                if not exists:
                    db.add(
                        Checkin(
                            gym_id=gym.id,
                            member_id=m.id,
                            checkin_at=dt,
                            source=CheckinSource.MANUAL,
                            hour_bucket=dt.hour,
                            weekday=dt.weekday(),
                            extra_data={"seed_tag": TAG, "edge_streak": True},
                        )
                    )

        # Extra leads with all stages and stale updated_at for automation
        new_leads = []
        stage_cycle = [
            LeadStage.NEW,
            LeadStage.CONTACT,
            LeadStage.VISIT,
            LeadStage.TRIAL,
            LeadStage.PROPOSAL,
            LeadStage.WON,
            LeadStage.LOST,
        ]
        sources = ["instagram", "google", "indicacao", "whatsapp", "site", "tiktok", "meta_ads"]
        winners = pick(active, 15)
        widx = 0
        for i in range(1, 29):
            st = stage_cycle[(i - 1) % len(stage_cycle)]
            converted = None
            if st == LeadStage.WON and widx < len(winners):
                converted = winners[widx].id
                widx += 1
            lead = Lead(
                gym_id=gym.id,
                owner_id=RND.choice(users).id if users else None,
                converted_member_id=converted,
                full_name=f"[{TAG}] Edge Lead {i:03d}",
                email=f"{TAG.lower()}.edge.lead{i:03d}@demo.com",
                phone=f"11{RND.randint(900000000, 999999999)}",
                source=RND.choice(sources),
                stage=st,
                estimated_value=RND.uniform(90, 2500),
                acquisition_cost=RND.uniform(0, 350),
                last_contact_at=now - timedelta(days=RND.randint(2, 45)),
                notes=[{"seed_tag": TAG, "edge": True}],
                lost_reason=RND.choice(["Sem retorno", "Preco", "Fechou com concorrente"]) if st == LeadStage.LOST else None,
            )
            if st not in {LeadStage.WON, LeadStage.LOST}:
                lead.updated_at = now - timedelta(days=RND.randint(8, 30))
            new_leads.append(lead)
        db.add_all(new_leads)

        # Edge tasks
        edge_tasks = []
        for m in pick(active, 40):
            st = RND.choice([TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE, TaskStatus.CANCELLED])
            due = now + timedelta(days=RND.randint(-25, 20))
            edge_tasks.append(
                Task(
                    gym_id=gym.id,
                    member_id=m.id,
                    assigned_to_user_id=m.assigned_user_id,
                    title=f"[{TAG}] Edge Task Member {m.full_name.split()[-1]}",
                    description="Caso limite para validacao de fluxo de tarefas.",
                    priority=RND.choice([TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.URGENT]),
                    status=st,
                    kanban_column=st.value,
                    due_date=due,
                    completed_at=(due + timedelta(days=1)) if st == TaskStatus.DONE else None,
                    suggested_message="Mensagem sugerida edge case",
                    extra_data={"seed_tag": TAG, "source": RND.choice(["manual", "automation", "onboarding", "plan_followup"]), "edge": True},
                )
            )

        for l in [ld for ld in new_leads if ld.stage not in {LeadStage.WON, LeadStage.LOST}][:16]:
            st = RND.choice([TaskStatus.TODO, TaskStatus.DOING, TaskStatus.DONE])
            edge_tasks.append(
                Task(
                    gym_id=gym.id,
                    lead_id=l.id,
                    assigned_to_user_id=l.owner_id,
                    title=f"[{TAG}] Edge Task Lead {l.full_name.split()[-1]}",
                    description="Follow-up comercial edge case.",
                    priority=RND.choice([TaskPriority.MEDIUM, TaskPriority.HIGH]),
                    status=st,
                    kanban_column=st.value,
                    due_date=now + timedelta(days=RND.randint(-20, 12)),
                    completed_at=(now - timedelta(days=RND.randint(1, 5))) if st == TaskStatus.DONE else None,
                    suggested_message="Mensagem comercial edge",
                    extra_data={"seed_tag": TAG, "source": "automation", "edge": True},
                )
            )
        db.add_all(edge_tasks)

        # NPS extremes (0..10)
        nps_rows = []
        score_cycle = list(range(0, 11)) * 5
        trig = [NPSTrigger.MONTHLY, NPSTrigger.AFTER_SIGNUP_7D, NPSTrigger.YELLOW_RISK, NPSTrigger.POST_CANCELLATION]
        for i, score in enumerate(score_cycle, start=1):
            m = members[(i - 1) % len(members)]
            rd = now - timedelta(days=RND.randint(0, 70))
            nps_rows.append(
                NPSResponse(
                    gym_id=gym.id,
                    member_id=m.id,
                    score=score,
                    comment=f"[{TAG}] Comentario NPS score {score}",
                    sentiment=sentiment(score),
                    sentiment_summary="edge sentiment summary",
                    trigger=trig[(i - 1) % len(trig)],
                    response_date=rd,
                    extra_data={"seed_tag": TAG, "edge": True},
                )
            )
            m.nps_last_score = score
            db.add(m)
        db.add_all(nps_rows)

        # Additional system notifications (without member)
        sys_notes = []
        for i in range(1, 31):
            sys_notes.append(
                InAppNotification(
                    gym_id=gym.id,
                    member_id=None,
                    user_id=RND.choice(users).id if users else None,
                    title=f"[{TAG}] System Notice {i:03d}",
                    message="Notificacao de sistema para teste de listagem e leitura.",
                    category="system",
                    read_at=None if i % 3 else now - timedelta(days=RND.randint(1, 10)),
                    extra_data={"seed_tag": TAG, "edge": True},
                )
            )
        db.add_all(sys_notes)

        # Extra audit logs
        audit_rows = []
        for i in range(1, 121):
            m = RND.choice(members)
            audit_rows.append(
                AuditLog(
                    gym_id=gym.id,
                    user_id=RND.choice(users).id if users else None,
                    member_id=m.id if i % 2 else None,
                    action=f"{TAG.lower()}_edge_action_{i % 12}",
                    entity=RND.choice(["member", "task", "lead", "automation", "nps", "system"]),
                    entity_id=m.id if i % 4 == 0 else None,
                    ip_address=f"10.77.0.{RND.randint(2, 240)}",
                    user_agent="seed-edge/1.0",
                    details={"seed_tag": TAG, "edge": True, "i": i},
                    created_at=now - timedelta(days=RND.randint(0, 40), hours=RND.randint(0, 23)),
                )
            )
        db.add_all(audit_rows)

        # Edge automation rules to cover all trigger/action combinations
        rules_to_ensure = [
            {
                "name": f"[{TAG}] Birthday Notify",
                "description": f"edge rule {TAG}",
                "trigger_type": "birthday",
                "trigger_config": {},
                "action_type": "notify",
                "action_config": {"title": "Aniversario: {nome}", "message": "Enviar felicitacoes", "category": "retention"},
            },
            {
                "name": f"[{TAG}] Streak Task",
                "description": f"edge rule {TAG}",
                "trigger_type": "checkin_streak",
                "trigger_config": {"streak_days": 7},
                "action_type": "create_task",
                "action_config": {"title": "Parabenizar streak: {nome}", "priority": "medium"},
            },
            {
                "name": f"[{TAG}] Inactivity Email",
                "description": f"edge rule {TAG}",
                "trigger_type": "inactivity_days",
                "trigger_config": {"days": 10},
                "action_type": "send_email",
                "action_config": {"subject": "Sentimos sua falta", "body": "Ola {nome}, voce esta ha {dias} dias sem check-in."},
            },
            {
                "name": f"[{TAG}] NPS Whatsapp",
                "description": f"edge rule {TAG}",
                "trigger_type": "nps_score",
                "trigger_config": {"max_score": 6},
                "action_type": "send_whatsapp",
                "action_config": {"template": "nps_low"},
            },
            {
                "name": f"[{TAG}] Lead Stale Notify",
                "description": f"edge rule {TAG}",
                "trigger_type": "lead_stale",
                "trigger_config": {"stale_days": 7},
                "action_type": "notify",
                "action_config": {"title": "Lead parado: {nome}", "message": "Lead parado ha {dias} dias", "category": "crm"},
            },
        ]

        for data in rules_to_ensure:
            exists = db.scalar(select(AutomationRule.id).where(AutomationRule.gym_id == gym.id, AutomationRule.name == data["name"]))
            if not exists:
                db.add(AutomationRule(gym_id=gym.id, is_active=True, executions_count=0, last_executed_at=None, **data))

        # Extra message logs in all statuses
        msg_rows = []
        for i in range(1, 81):
            m = RND.choice(members)
            status = RND.choice(["sent", "delivered", "read", "failed", "blocked", "skipped"])
            msg_rows.append(
                MessageLog(
                    gym_id=gym.id,
                    member_id=m.id,
                    automation_rule_id=None,
                    channel=RND.choice(["whatsapp", "email"]),
                    recipient=m.phone or m.email or f"edge{i}@demo.com",
                    template_name=RND.choice(["birthday", "nps_low", "reengagement_7d", None]),
                    content="Edge message log for QA",
                    status=status,
                    error_detail="simulated error" if status in {"failed", "blocked"} else None,
                    extra_data={"seed_tag": TAG, "edge": True, "i": i},
                    created_at=now - timedelta(days=RND.randint(0, 35), hours=RND.randint(0, 23)),
                )
            )
        db.add_all(msg_rows)

        db.commit()

        # Run automations once to materialize automatic side effects
        auto_results = run_automation_rules(db)
        db.commit()

        # refresh & cache bust
        try:
            refresh_member_kpis_materialized_view(db)
        except Exception as exc:
            print(f"WARN: materialized view: {exc}")
        invalidate_dashboard_cache("all", "members", "checkins", "leads", "nps", "risk", "tasks", "financial", gym_id=gym.id)

        tag_members = db.scalar(select(func.count()).select_from(Member).where(Member.gym_id == gym.id, Member.full_name.like(f"[{TAG}]%"), Member.deleted_at.is_(None)))
        tag_leads = db.scalar(select(func.count()).select_from(Lead).where(Lead.gym_id == gym.id, Lead.full_name.like(f"[{TAG}]%"), Lead.deleted_at.is_(None)))
        tag_tasks = db.scalar(select(func.count()).select_from(Task).where(Task.gym_id == gym.id, Task.title.like(f"[{TAG}]%"), Task.deleted_at.is_(None)))
        no_email = db.scalar(select(func.count()).select_from(Member).where(Member.gym_id == gym.id, Member.full_name.like(f"[{TAG}]%"), Member.email.is_(None), Member.deleted_at.is_(None)))
        no_phone = db.scalar(select(func.count()).select_from(Member).where(Member.gym_id == gym.id, Member.full_name.like(f"[{TAG}]%"), Member.phone.is_(None), Member.deleted_at.is_(None)))

        print("EDGE_SEED_OK")
        print(f"SEED_TAG={TAG}")
        print(f"tag_members={tag_members}")
        print(f"tag_leads={tag_leads}")
        print(f"tag_tasks={tag_tasks}")
        print(f"tag_members_no_email={no_email}")
        print(f"tag_members_no_phone={no_phone}")
        print(f"automation_results={len(auto_results)}")

    finally:
        clear_current_gym_id()
        db.close()


if __name__ == "__main__":
    main()
