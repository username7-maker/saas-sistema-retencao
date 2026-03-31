from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActuarMemberLink, Member
from app.utils.encryption import decrypt_cpf

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ActuarMemberResolution:
    status: str
    error_code: str | None = None
    member_context: dict | None = None
    actuar_external_id: str | None = None
    match_confidence: float | None = None
    action_log: list[dict] | None = None


def get_actuar_member_link(db: Session, *, gym_id: UUID, member_id: UUID) -> ActuarMemberLink | None:
    return db.scalar(
        select(ActuarMemberLink).where(
            ActuarMemberLink.gym_id == gym_id,
            ActuarMemberLink.member_id == member_id,
        )
    )


def upsert_actuar_member_link(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    user_id: UUID | None,
    actuar_external_id: str | None,
    actuar_search_name: str | None,
    actuar_search_document: str | None,
    actuar_search_birthdate,
    match_confidence: float | None,
) -> ActuarMemberLink:
    link = get_actuar_member_link(db, gym_id=gym_id, member_id=member_id)
    if link is None:
        link = ActuarMemberLink(
            gym_id=gym_id,
            member_id=member_id,
        )
        db.add(link)
    link.actuar_external_id = (actuar_external_id or None)
    link.actuar_search_name = actuar_search_name or None
    link.actuar_search_document = normalize_document(actuar_search_document) if actuar_search_document else None
    link.actuar_search_birthdate = actuar_search_birthdate
    link.linked_at = datetime.now(timezone.utc)
    link.linked_by_user_id = user_id
    link.match_confidence = match_confidence
    link.is_active = True
    db.flush()
    return link


def resolve_actuar_member(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    provider,
    user_id: UUID | None = None,
) -> ActuarMemberResolution:
    link = get_actuar_member_link(db, gym_id=gym_id, member_id=member.id)
    action_log: list[dict] = []

    if link and link.is_active and link.actuar_external_id:
        action_log.append({"strategy": "linked_external_id", "result": "matched"})
        return ActuarMemberResolution(
            status="matched",
            actuar_external_id=link.actuar_external_id,
            member_context={"external_id": link.actuar_external_id},
            match_confidence=float(link.match_confidence) if link.match_confidence is not None else 1.0,
            action_log=action_log,
        )

    document = resolve_member_document_for_actuar(member, link)
    if document:
        lookup = provider.find_member({"document": document, "strategy": "document"})
        action_log.append({"strategy": "document", "result": lookup.get("status")})
        resolution = _resolution_from_lookup(
            db,
            gym_id=gym_id,
            member=member,
            lookup=lookup,
            action_log=action_log,
            user_id=user_id,
            document=document,
            link=link,
        )
        if resolution.status != "not_found":
            return resolution

    if not member.birthdate:
        action_log.append({"strategy": "birthdate_missing", "result": "needs_review"})
        return ActuarMemberResolution(status="needs_review", error_code="member_not_linked", action_log=action_log)

    lookup = provider.find_member(
        {
            "full_name": member.full_name,
            "birthdate": member.birthdate.isoformat(),
            "strategy": "exact_name_birthdate",
        }
    )
    action_log.append({"strategy": "exact_name_birthdate", "result": lookup.get("status")})
    resolution = _resolution_from_lookup(
        db,
        gym_id=gym_id,
        member=member,
        lookup=lookup,
        action_log=action_log,
        user_id=user_id,
        document=document,
        link=link,
    )
    if resolution.status != "not_found":
        return resolution

    lookup = provider.find_member(
        {
            "full_name": member.full_name,
            "birthdate": member.birthdate.isoformat(),
            "approximate": True,
            "strategy": "approx_name_birthdate",
        }
    )
    action_log.append({"strategy": "approx_name_birthdate", "result": lookup.get("status")})
    resolution = _resolution_from_lookup(
        db,
        gym_id=gym_id,
        member=member,
        lookup=lookup,
        action_log=action_log,
        user_id=user_id,
        document=document,
        link=link,
    )
    if resolution.status != "not_found":
        return resolution

    return ActuarMemberResolution(status="needs_review", error_code="member_not_found", action_log=action_log)


def normalize_document(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(ch for ch in value if ch.isdigit())
    return normalized or None


def mask_document(value: str | None) -> str | None:
    normalized = normalize_document(value)
    if not normalized:
        return None
    if len(normalized) <= 4:
        return "*" * len(normalized)
    return f"{'*' * (len(normalized) - 4)}{normalized[-4:]}"


def resolve_member_document_for_actuar(member: Member, link: ActuarMemberLink | None) -> str | None:
    if link and link.actuar_search_document:
        return normalize_document(link.actuar_search_document)
    encrypted_cpf = getattr(member, "cpf_encrypted", None)
    if not encrypted_cpf:
        return None
    try:
        return normalize_document(decrypt_cpf(encrypted_cpf))
    except Exception:
        logger.warning("Failed to decrypt member document for Actuar matching.", extra={"extra_fields": {"event": "actuar_member_document_unavailable", "member_id": str(member.id)}})
        return None


def _resolution_from_lookup(
    db: Session,
    *,
    gym_id: UUID,
    member: Member,
    lookup: dict,
    action_log: list[dict],
    user_id: UUID | None,
    document: str | None,
    link: ActuarMemberLink | None,
) -> ActuarMemberResolution:
    status = lookup.get("status") or "not_found"
    if status == "matched":
        member_context = lookup.get("member_context") or {}
        actuar_external_id = lookup.get("actuar_external_id") or member_context.get("external_id")
        confidence = lookup.get("match_confidence")
        upsert_actuar_member_link(
            db,
            gym_id=gym_id,
            member_id=member.id,
            user_id=user_id,
            actuar_external_id=actuar_external_id,
            actuar_search_name=getattr(link, "actuar_search_name", None) or member.full_name,
            actuar_search_document=document,
            actuar_search_birthdate=member.birthdate,
            match_confidence=confidence,
        )
        return ActuarMemberResolution(
            status="matched",
            actuar_external_id=actuar_external_id,
            member_context=member_context or {"external_id": actuar_external_id},
            match_confidence=confidence,
            action_log=action_log,
        )
    if status == "ambiguous":
        return ActuarMemberResolution(status="needs_review", error_code="member_match_ambiguous", action_log=action_log)
    if status == "not_found":
        return ActuarMemberResolution(status="not_found", error_code="member_not_found", action_log=action_log)
    return ActuarMemberResolution(status="needs_review", error_code=lookup.get("error_code") or "member_not_linked", action_log=action_log)
