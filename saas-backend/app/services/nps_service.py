from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Member, MemberStatus, NPSSentiment, NPSTrigger, NPSResponse, RiskLevel
from app.schemas import NPSEvolutionPoint, NPSResponseCreate
from app.services.audit_service import log_audit_event
from app.utils.claude import analyze_sentiment
from app.utils.email import send_email


def create_response(db: Session, payload: NPSResponseCreate) -> NPSResponse:
    sentiment, summary = analyze_sentiment(payload.score, payload.comment)
    response = NPSResponse(
        member_id=payload.member_id,
        score=payload.score,
        comment=payload.comment,
        sentiment=sentiment,
        sentiment_summary=summary,
        trigger=payload.trigger,
    )
    db.add(response)

    if payload.member_id:
        member = db.get(Member, payload.member_id)
        if member:
            member.nps_last_score = payload.score
            db.add(member)
            if sentiment == NPSSentiment.NEGATIVE:
                log_audit_event(
                    db,
                    action="nps_detractor_alert",
                    entity="member",
                    member_id=member.id,
                    entity_id=member.id,
                    details={"score": payload.score, "summary": summary},
                )

    db.commit()
    db.refresh(response)
    return response


def run_nps_dispatch(db: Session) -> dict[str, int]:
    today = date.today()
    sent_counts = {
        NPSTrigger.AFTER_SIGNUP_7D.value: 0,
        NPSTrigger.MONTHLY.value: 0,
        NPSTrigger.YELLOW_RISK.value: 0,
        NPSTrigger.POST_CANCELLATION.value: 0,
    }

    members = db.scalars(select(Member).where(Member.deleted_at.is_(None))).all()
    for member in members:
        if _should_send_after_signup_7d(db, member, today):
            if _send_nps_email(db, member, NPSTrigger.AFTER_SIGNUP_7D):
                sent_counts[NPSTrigger.AFTER_SIGNUP_7D.value] += 1
        if _should_send_monthly(db, member, today):
            if _send_nps_email(db, member, NPSTrigger.MONTHLY):
                sent_counts[NPSTrigger.MONTHLY.value] += 1
        if member.risk_level == RiskLevel.YELLOW and _recent_send_missing(db, member.id, "nps_sent_yellow", 30):
            if _send_nps_email(db, member, NPSTrigger.YELLOW_RISK):
                sent_counts[NPSTrigger.YELLOW_RISK.value] += 1
        if member.status == MemberStatus.CANCELLED and _recent_send_missing(db, member.id, "nps_sent_cancelled", 365):
            if _send_nps_email(db, member, NPSTrigger.POST_CANCELLATION):
                sent_counts[NPSTrigger.POST_CANCELLATION.value] += 1

    db.commit()
    return sent_counts


def nps_evolution(db: Session, months: int = 12) -> list[NPSEvolutionPoint]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=31 * months)
    rows = db.execute(
        select(
            func.to_char(NPSResponse.response_date, "YYYY-MM").label("month"),
            func.avg(NPSResponse.score).label("avg_score"),
            func.count().label("responses"),
        )
        .where(NPSResponse.response_date >= since)
        .group_by(func.to_char(NPSResponse.response_date, "YYYY-MM"))
        .order_by(func.to_char(NPSResponse.response_date, "YYYY-MM"))
    ).all()
    return [
        NPSEvolutionPoint(
            month=row.month,
            average_score=float(row.avg_score or 0),
            responses=int(row.responses or 0),
        )
        for row in rows
    ]


def detractors_alerts(db: Session, days: int = 30) -> list[NPSResponse]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    return db.scalars(
        select(NPSResponse).where(
            NPSResponse.response_date >= since,
            NPSResponse.score <= 6,
        )
    ).all()


def _should_send_after_signup_7d(db: Session, member: Member, today: date) -> bool:
    if member.status != MemberStatus.ACTIVE:
        return False
    if (today - member.join_date).days < 7:
        return False
    return _recent_send_missing(db, member.id, "nps_sent_after_signup", 3650)


def _should_send_monthly(db: Session, member: Member, today: date) -> bool:
    if member.status != MemberStatus.ACTIVE:
        return False
    start_month = datetime.combine(today.replace(day=1), datetime.min.time(), tzinfo=timezone.utc)
    existing = db.scalar(
        select(AuditLog).where(
            AuditLog.member_id == member.id,
            AuditLog.action == "nps_sent_monthly",
            AuditLog.created_at >= start_month,
        )
    )
    return existing is None


def _recent_send_missing(db: Session, member_id, action: str, days: int) -> bool:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    existing = db.scalar(
        select(AuditLog).where(
            AuditLog.member_id == member_id,
            AuditLog.action == action,
            AuditLog.created_at >= cutoff,
        )
    )
    return existing is None


def _send_nps_email(db: Session, member: Member, trigger: NPSTrigger) -> bool:
    if not member.email:
        return False
    sent = send_email(
        member.email,
        "Pesquisa NPS AI GYM OS",
        f"Ola {member.full_name}, compartilhe seu NPS para melhorarmos sua experiencia.",
    )
    if not sent:
        return False
    action_map = {
        NPSTrigger.AFTER_SIGNUP_7D: "nps_sent_after_signup",
        NPSTrigger.MONTHLY: "nps_sent_monthly",
        NPSTrigger.YELLOW_RISK: "nps_sent_yellow",
        NPSTrigger.POST_CANCELLATION: "nps_sent_cancelled",
    }
    log_audit_event(
        db,
        action=action_map[trigger],
        entity="member",
        member_id=member.id,
        entity_id=member.id,
        details={"trigger": trigger.value},
    )
    return True
