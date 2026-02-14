from cachetools import TTLCache


dashboard_cache = TTLCache(maxsize=256, ttl=300)


def make_cache_key(namespace: str, *parts: object) -> str:
    suffix = ":".join(str(part) for part in parts)
    return f"{namespace}:{suffix}"
