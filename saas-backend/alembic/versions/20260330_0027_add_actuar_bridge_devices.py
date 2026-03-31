"""add actuar bridge devices

Revision ID: 20260330_0027
Revises: 20260330_0026
Create Date: 2026-03-30 23:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260330_0027"
down_revision = "20260330_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actuar_bridge_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pairing"),
        sa.Column("pairing_code_hash", sa.Text(), nullable=True),
        sa.Column("pairing_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auth_token_hash", sa.Text(), nullable=True),
        sa.Column("bridge_version", sa.String(length=40), nullable=True),
        sa.Column("browser_name", sa.String(length=80), nullable=True),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pairing', 'online', 'offline', 'revoked')",
            name="actuar_bridge_devices_status_valid",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actuar_bridge_devices_gym_id", "actuar_bridge_devices", ["gym_id"], unique=False)
    op.create_index("ix_actuar_bridge_devices_gym_status", "actuar_bridge_devices", ["gym_id", "status"], unique=False)
    op.create_index("ix_actuar_bridge_devices_gym_last_seen", "actuar_bridge_devices", ["gym_id", "last_seen_at"], unique=False)

    op.drop_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_mode_valid",
        "body_composition_evaluations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_mode_valid",
        "body_composition_evaluations",
        "actuar_sync_mode IN ('disabled', 'http_api', 'csv_export', 'assisted_rpa', 'local_bridge')",
    )

    op.drop_constraint("actuar_sync_jobs_status_valid", "actuar_sync_jobs", type_="check")
    op.create_check_constraint(
        "actuar_sync_jobs_status_valid",
        "actuar_sync_jobs",
        "status IN ('pending', 'processing', 'synced', 'failed', 'needs_review', 'cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("actuar_sync_jobs_status_valid", "actuar_sync_jobs", type_="check")
    op.create_check_constraint(
        "actuar_sync_jobs_status_valid",
        "actuar_sync_jobs",
        "status IN ('pending', 'processing', 'synced', 'failed', 'needs_review', 'cancelled')",
    )

    op.drop_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_mode_valid",
        "body_composition_evaluations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_body_composition_evaluations_bce_actuar_sync_mode_valid",
        "body_composition_evaluations",
        "actuar_sync_mode IN ('disabled', 'http_api', 'csv_export', 'assisted_rpa')",
    )

    op.drop_index("ix_actuar_bridge_devices_gym_last_seen", table_name="actuar_bridge_devices")
    op.drop_index("ix_actuar_bridge_devices_gym_status", table_name="actuar_bridge_devices")
    op.drop_index("ix_actuar_bridge_devices_gym_id", table_name="actuar_bridge_devices")
    op.drop_table("actuar_bridge_devices")
