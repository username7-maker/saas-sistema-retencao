"""Encrypt phone columns (LGPD compliance).

Changes phone columns from VARCHAR(32) to TEXT to accommodate encrypted values.
Encrypts existing plain-text phone data using AES-256-GCM.

Revision ID: 20260311_0018
Revises: 20260310_0017
Create Date: 2026-03-11
"""

import base64
import os

import sqlalchemy as sa
from alembic import op
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

revision = "20260311_0018"
down_revision = "20260310_0017"
branch_labels = None
depends_on = None


def _get_encryption_key() -> bytes:
    """Resolve encryption key from environment (same logic as app.utils.encryption)."""
    import hashlib

    raw_key = os.environ.get("CPF_ENCRYPTION_KEY", "").strip()
    if not raw_key or raw_key in ("change-me-with-64-hex", "change-me"):
        raise RuntimeError(
            "CPF_ENCRYPTION_KEY must be set to run this migration. "
            "It is required to encrypt existing phone numbers."
        )
    if len(raw_key) == 64:
        try:
            return bytes.fromhex(raw_key)
        except ValueError:
            pass
    try:
        decoded = base64.urlsafe_b64decode(raw_key.encode("utf-8"))
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


def _encrypt(plain: str, key: bytes) -> str:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plain.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def upgrade() -> None:
    key = _get_encryption_key()

    # 1. Alter column types from VARCHAR(32) to TEXT
    for table in ("members", "leads", "users"):
        op.alter_column(table, "phone", type_=sa.Text(), existing_type=sa.String(32))

    # 2. Encrypt existing phone data in batches
    conn = op.get_bind()
    for table_name in ("members", "leads", "users"):
        t = sa.table(table_name, sa.column("id", sa.Uuid), sa.column("phone", sa.Text))
        rows = conn.execute(
            sa.select(t.c.id, t.c.phone).where(
                t.c.phone.is_not(None),
                t.c.phone != "",
            )
        ).fetchall()

        for row_id, phone_plain in rows:
            encrypted = _encrypt(phone_plain, key)
            conn.execute(
                sa.update(t).where(t.c.id == row_id).values(phone=encrypted)
            )


def downgrade() -> None:
    # NOTE: Downgrade decrypts phone values back to plain text.
    # This requires CPF_ENCRYPTION_KEY to be set.
    key = _get_encryption_key()
    conn = op.get_bind()

    for table_name in ("members", "leads", "users"):
        t = sa.table(table_name, sa.column("id", sa.Uuid), sa.column("phone", sa.Text))
        rows = conn.execute(
            sa.select(t.c.id, t.c.phone).where(
                t.c.phone.is_not(None),
                t.c.phone != "",
            )
        ).fetchall()

        for row_id, phone_enc in rows:
            try:
                payload = base64.urlsafe_b64decode(phone_enc.encode("utf-8"))
                nonce, ciphertext = payload[:12], payload[12:]
                aesgcm = AESGCM(key)
                plain = aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
                conn.execute(
                    sa.update(t).where(t.c.id == row_id).values(phone=plain)
                )
            except Exception:
                pass  # Already plain text, skip

    for table in ("members", "leads", "users"):
        op.alter_column(table, "phone", type_=sa.String(32), existing_type=sa.Text())
