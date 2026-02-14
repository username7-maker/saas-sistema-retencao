import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _get_key() -> bytes:
    raw_key = settings.cpf_encryption_key.strip()
    if not raw_key:
        return hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()

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


def encrypt_cpf(cpf_plain: str) -> str:
    nonce = os.urandom(12)
    aesgcm = AESGCM(_get_key())
    ciphertext = aesgcm.encrypt(nonce, cpf_plain.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_cpf(cpf_encrypted: str) -> str:
    payload = base64.urlsafe_b64decode(cpf_encrypted.encode("utf-8"))
    nonce, ciphertext = payload[:12], payload[12:]
    aesgcm = AESGCM(_get_key())
    plain_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plain_bytes.decode("utf-8")
