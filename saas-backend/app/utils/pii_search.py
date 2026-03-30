import base64
import hashlib
import hmac

from app.core.config import settings


def extract_digits(value: str | None) -> str:
    if not value:
        return ""
    return "".join(char for char in str(value) if char.isdigit())


def normalize_phone_for_search(value: str | None) -> str | None:
    digits = extract_digits(value)
    if not digits:
        return None
    if not digits.startswith("55") and len(digits) in {10, 11}:
        digits = f"55{digits}"
    if len(digits) < 10:
        return None
    return digits


def normalize_cpf_for_search(value: str | None) -> str | None:
    digits = extract_digits(value)
    if len(digits) != 11:
        return None
    return digits


def _search_key_bytes() -> bytes:
    raw_key = (settings.pii_search_key or settings.cpf_encryption_key or "").strip()
    if not raw_key:
        return b"change-me"

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

    return raw_key.encode("utf-8")


def build_pii_search_hash(value: str | None) -> str | None:
    if not value:
        return None
    return hmac.new(_search_key_bytes(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def build_phone_search_hash(value: str | None) -> str | None:
    return build_pii_search_hash(normalize_phone_for_search(value))


def build_cpf_search_hash(value: str | None) -> str | None:
    return build_pii_search_hash(normalize_cpf_for_search(value))
