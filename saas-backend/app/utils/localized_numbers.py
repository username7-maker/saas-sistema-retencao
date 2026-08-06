from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any


_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")
_SUPPORTED_UNIT_RE = re.compile(r"(%|kg|kcal|cm|mm)$", re.IGNORECASE)


class LocalizedNumberError(ValueError):
    pass


def parse_localized_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    if isinstance(value, bool):
        raise LocalizedNumberError("boolean is not a numeric measurement")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise LocalizedNumberError("number is not finite")
        return Decimal(str(value))
    if not isinstance(value, str):
        raise LocalizedNumberError("unsupported numeric value")

    compact = re.sub(r"\s+", "", value.strip())
    if not compact:
        return None

    without_unit = _SUPPORTED_UNIT_RE.sub("", compact)
    if not without_unit:
        return None
    if "," in without_unit and "." in without_unit:
        raise LocalizedNumberError("ambiguous decimal/thousands separators")

    normalized = without_unit.replace(",", ".")
    if not _DECIMAL_RE.fullmatch(normalized):
        raise LocalizedNumberError("invalid numeric format")

    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise LocalizedNumberError("invalid decimal") from exc


def parse_localized_float(value: Any) -> float | None:
    parsed = parse_localized_decimal(value)
    return float(parsed) if parsed is not None else None
