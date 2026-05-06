import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class MemberNote(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "member_notes"
    __table_args__ = (
        Index("ix_member_notes_gym_member_created", "gym_id", "member_id", "created_at"),
        Index("ix_member_notes_gym_type_created", "gym_id", "note_type", "created_at"),
        Index("ix_member_notes_author_created", "author_user_id", "created_at"),
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
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note_type: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(40), nullable=False, default="internal")
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    member = relationship("Member")
    author = relationship("User")
