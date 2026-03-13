import base64
import hashlib
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_key() -> bytes:
    raw_key = settings.cpf_encryption_key.strip()
    if not raw_key or raw_key in ("change-me-with-64-hex", "change-me"):
        raise RuntimeError(
            "CPF_ENCRYPTION_KEY nao configurada. "
            "Defina uma chave AES-256 de 64 caracteres hexadecimais na variavel de ambiente."
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


def encrypt_pii(plain: str) -> str:
    """Encrypt any PII string with AES-256-GCM."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(_get_key())
    ciphertext = aesgcm.encrypt(nonce, plain.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_pii(encrypted: str) -> str:
    """Decrypt any PII string encrypted with AES-256-GCM."""
    payload = base64.urlsafe_b64decode(encrypted.encode("utf-8"))
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(_get_key())
    plain_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plain_bytes.decode("utf-8")


# Keep backwards-compatible aliases for CPF
encrypt_cpf = encrypt_pii
decrypt_cpf = decrypt_pii


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts/decrypts PII at rest.

    Usage in models:
        phone: Mapped[str | None] = mapped_column(EncryptedString(), nullable=True)

    Stores AES-256-GCM encrypted base64 in the DB.
    Returns plain text to Python code — zero changes needed in services.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None or value == "":
            return value
        try:
            return encrypt_pii(value)
        except Exception:
            logger.warning("Failed to encrypt PII value, storing as-is")
            return value

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None or value == "":
            return value
        try:
            return decrypt_pii(value)
        except Exception:
            # Value may be plain text (pre-migration data) — return as-is
            return value
