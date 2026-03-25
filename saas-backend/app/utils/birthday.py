import re
import unicodedata
from datetime import date


_PT_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_BIRTHDAY_LABEL_PATTERN = re.compile(r"^\s*(\d{1,2})\s+de\s+(.+?)\s*$", flags=re.IGNORECASE)


def normalize_month_token(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )


def parse_birthday_label(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None

    match = _BIRTHDAY_LABEL_PATTERN.match(value)
    if not match:
        return None

    try:
        day = int(match.group(1))
    except ValueError:
        return None

    month = _PT_MONTHS.get(normalize_month_token(match.group(2)))
    if month is None or day < 1 or day > 31:
        return None

    return day, month


def birthday_label_matches_today(value: object, today: date) -> bool:
    parsed = parse_birthday_label(value)
    if parsed is None:
        return False
    day, month = parsed
    return day == today.day and month == today.month
