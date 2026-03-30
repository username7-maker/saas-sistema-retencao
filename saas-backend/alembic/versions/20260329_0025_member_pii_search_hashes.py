"""add member pii search hashes

Revision ID: 20260329_0025
Revises: 20260329_0024
"""

from alembic import op
import sqlalchemy as sa

from app.utils.encryption import decrypt_cpf, decrypt_pii
from app.utils.pii_search import build_cpf_search_hash, build_phone_search_hash


revision = "20260329_0025"
down_revision = "20260329_0024"
branch_labels = None
depends_on = None


def _safe_decrypt_phone(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return decrypt_pii(value)
    except Exception:
        return value


def _safe_decrypt_cpf(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return decrypt_cpf(value)
    except Exception:
        return value


def upgrade() -> None:
    op.add_column("members", sa.Column("phone_search_hash", sa.String(length=64), nullable=True))
    op.add_column("members", sa.Column("cpf_search_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_members_gym_phone_search_hash", "members", ["gym_id", "phone_search_hash"], unique=False)
    op.create_index("ix_members_gym_cpf_search_hash", "members", ["gym_id", "cpf_search_hash"], unique=False)

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, phone, cpf_encrypted FROM members")).mappings().all()
    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE members
                SET phone_search_hash = :phone_search_hash,
                    cpf_search_hash = :cpf_search_hash
                WHERE id = :member_id
                """
            ),
            {
                "member_id": row["id"],
                "phone_search_hash": build_phone_search_hash(_safe_decrypt_phone(row["phone"])),
                "cpf_search_hash": build_cpf_search_hash(_safe_decrypt_cpf(row["cpf_encrypted"])),
            },
        )


def downgrade() -> None:
    op.drop_index("ix_members_gym_cpf_search_hash", table_name="members")
    op.drop_index("ix_members_gym_phone_search_hash", table_name="members")
    op.drop_column("members", "cpf_search_hash")
    op.drop_column("members", "phone_search_hash")
