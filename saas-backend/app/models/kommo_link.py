import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KommoMemberLink(Base, TimestampMixin):
    __tablename__ = "kommo_member_links"
    __table_args__ = (
        UniqueConstraint("gym_id", "member_id", name="uq_kommo_member_links_gym_member"),
        Index("ix_kommo_member_links_gym_lead", "gym_id", "kommo_lead_id"),
        Index("ix_kommo_member_links_gym_contact", "gym_id", "kommo_contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kommo_contact_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kommo_lead_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_handoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_type: Mapped[str | None] = mapped_column(String(40), nullable=True)


class KommoDomainRoute(Base, TimestampMixin):
    __tablename__ = "kommo_domain_routes"
    __table_args__ = (
        UniqueConstraint("gym_id", "domain", name="uq_kommo_domain_routes_gym_domain"),
        Index("ix_kommo_domain_routes_gym_domain", "gym_id", "domain"),
        Index("ix_kommo_domain_routes_gym_enabled", "gym_id", "is_enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(40), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    pipeline_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stage_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    salesbot_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    channel_source_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    responsible_user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pdf_url_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pdf_delivery_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="native_file_required", server_default="native_file_required")
    file_uuid_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_name_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_attachment_note_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_type_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_id_field_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class KommoFileAttachment(Base, TimestampMixin):
    __tablename__ = "kommo_file_attachments"
    __table_args__ = (
        UniqueConstraint("gym_id", "domain", "source_type", "source_id", name="uq_kommo_file_attachments_source"),
        Index("ix_kommo_file_attachments_gym_member", "gym_id", "member_id"),
        Index("ix_kommo_file_attachments_gym_lead", "gym_id", "kommo_lead_id"),
        Index("ix_kommo_file_attachments_gym_status", "gym_id", "upload_status", "attach_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    kommo_lead_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kommo_contact_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_uuid: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    attach_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    delivery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class KommoMemberDomainLink(Base, TimestampMixin):
    __tablename__ = "kommo_member_domain_links"
    __table_args__ = (
        UniqueConstraint("gym_id", "member_id", "domain", name="uq_kommo_member_domain_links_gym_member_domain"),
        Index("ix_kommo_member_domain_links_gym_domain_lead", "gym_id", "domain", "kommo_lead_id"),
        Index("ix_kommo_member_domain_links_gym_domain_contact", "gym_id", "domain", "kommo_contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gym_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gyms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(40), nullable=False)
    kommo_contact_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kommo_lead_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_salesbot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_handoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_action_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
