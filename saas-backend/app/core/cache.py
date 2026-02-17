import logging
import pickle
from collections import defaultdict
from collections.abc import Iterable
from threading import RLock
from uuid import UUID

from cachetools import TTLCache

from app.core.config import settings
from app.database import get_current_gym_id

try:
    from redis import Redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - fallback when redis is not installed
    Redis = None  # type: ignore[assignment,misc]

    class RedisError(Exception):
        pass


logger = logging.getLogger(__name__)

DASHBOARD_NAMESPACES: frozenset[str] = frozenset(
    {
        "dashboard_executive",
        "dashboard_mrr",
        "dashboard_churn",
        "dashboard_ltv",
        "dashboard_growth",
        "dashboard_operational",
        "dashboard_commercial",
        "dashboard_financial",
        "dashboard_retention",
        "dashboard_insight_executive",
        "dashboard_insight_retention",
    }
)

DASHBOARD_NAMESPACES_BY_DOMAIN: dict[str, set[str]] = {
    "all": set(DASHBOARD_NAMESPACES),
    "members": {
        "dashboard_executive",
        "dashboard_mrr",
        "dashboard_churn",
        "dashboard_ltv",
        "dashboard_growth",
        "dashboard_operational",
        "dashboard_financial",
        "dashboard_retention",
        "dashboard_insight_executive",
        "dashboard_insight_retention",
    },
    "checkins": {
        "dashboard_executive",
        "dashboard_operational",
        "dashboard_retention",
        "dashboard_insight_executive",
        "dashboard_insight_retention",
    },
    "leads": {"dashboard_commercial"},
    "nps": {
        "dashboard_executive",
        "dashboard_retention",
        "dashboard_insight_executive",
        "dashboard_insight_retention",
    },
    "risk": {
        "dashboard_executive",
        "dashboard_retention",
        "dashboard_insight_executive",
        "dashboard_insight_retention",
    },
    "tasks": {"dashboard_operational", "dashboard_commercial", "dashboard_retention"},
    "financial": {
        "dashboard_executive",
        "dashboard_mrr",
        "dashboard_churn",
        "dashboard_ltv",
        "dashboard_growth",
        "dashboard_financial",
        "dashboard_insight_executive",
    },
}


class DashboardCache:
    def __init__(
        self,
        *,
        maxsize: int,
        default_ttl: int,
        redis_url: str = "",
        key_prefix: str = "aigymos:dashboard-cache",
    ) -> None:
        self._default_ttl = max(1, int(default_ttl))
        self._key_prefix = key_prefix
        self._local_cache: TTLCache[str, object] = TTLCache(maxsize=maxsize, ttl=self._default_ttl)
        self._local_index: dict[str, set[str]] = defaultdict(set)
        self._lock = RLock()
        self._redis: Redis | None = None
        self._redis_configured = bool(redis_url)
        self._redis_enabled = False
        self._load_redis(redis_url)

    def _load_redis(self, redis_url: str) -> None:
        if not redis_url or Redis is None:
            if redis_url and Redis is None:
                logger.warning("REDIS_URL definido, mas pacote redis nao esta disponivel. Usando cache em memoria.")
            return
        try:
            client = Redis.from_url(redis_url, decode_responses=False)  # type: ignore[union-attr]
            client.ping()
            self._redis = client
            self._redis_enabled = True
            logger.info("Cache distribuido Redis habilitado.")
        except Exception:
            logger.exception("Falha ao conectar Redis. Usando cache local em memoria.")
            self._redis = None
            self._redis_enabled = False

    def _data_key(self, cache_key: str) -> str:
        return f"{self._key_prefix}:data:{cache_key}"

    def _index_key(self, tenant_scope: str, namespace: str) -> str:
        return f"{self._key_prefix}:index:{tenant_scope}:{namespace}"

    @staticmethod
    def _split_cache_key(cache_key: str) -> tuple[str, str] | None:
        first, sep, rest = cache_key.partition(":")
        if not sep:
            return None
        namespace, sep2, _suffix = rest.partition(":")
        if not sep2 and not namespace:
            return None
        if not namespace:
            return None
        return first, namespace

    def _register_local_key(self, cache_key: str) -> None:
        split = self._split_cache_key(cache_key)
        if not split:
            return
        tenant_scope, namespace = split
        idx_key = self._index_key(tenant_scope, namespace)
        self._local_index[idx_key].add(cache_key)

    def _remove_local_key(self, cache_key: str) -> None:
        self._local_cache.pop(cache_key, None)
        dead_index_keys: list[str] = []
        for idx_key, keys in self._local_index.items():
            keys.discard(cache_key)
            if not keys:
                dead_index_keys.append(idx_key)
        for idx_key in dead_index_keys:
            self._local_index.pop(idx_key, None)

    def _mark_redis_down(self, exc: Exception) -> None:
        if self._redis_enabled:
            logger.warning("Redis indisponivel durante operacao de cache. Fallback para memoria: %s", exc)
        self._redis_enabled = False

    def get(self, cache_key: str) -> object | None:
        if self._redis_enabled and self._redis is not None:
            try:
                payload = self._redis.get(self._data_key(cache_key))
                if payload is not None:
                    value = pickle.loads(payload)
                    with self._lock:
                        self._local_cache[cache_key] = value
                        self._register_local_key(cache_key)
                    return value
            except RedisError as exc:
                self._mark_redis_down(exc)
            except (pickle.PickleError, EOFError, AttributeError, ValueError, TypeError) as exc:
                logger.warning("Payload de cache invalido para chave %s: %s", cache_key, exc)
                try:
                    self._redis.delete(self._data_key(cache_key))
                except RedisError:
                    self._mark_redis_down(exc if isinstance(exc, Exception) else Exception("cache_error"))

        with self._lock:
            return self._local_cache.get(cache_key)

    def set(self, cache_key: str, value: object, *, ttl: int | None = None) -> None:
        ttl_seconds = max(1, int(ttl or self._default_ttl))
        with self._lock:
            self._local_cache[cache_key] = value
            self._register_local_key(cache_key)

        if self._redis_enabled and self._redis is not None:
            try:
                payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                split = self._split_cache_key(cache_key)
                pipe = self._redis.pipeline()
                pipe.set(self._data_key(cache_key), payload, ex=ttl_seconds)
                if split:
                    tenant_scope, namespace = split
                    idx_key = self._index_key(tenant_scope, namespace)
                    pipe.sadd(idx_key, self._data_key(cache_key))
                    pipe.expire(idx_key, max(ttl_seconds * 2, ttl_seconds + 60))
                pipe.execute()
            except RedisError as exc:
                self._mark_redis_down(exc)
            except (pickle.PickleError, TypeError, ValueError) as exc:
                logger.warning("Falha ao serializar cache para chave %s. Mantendo somente cache local: %s", cache_key, exc)

    def delete(self, cache_key: str) -> None:
        with self._lock:
            self._remove_local_key(cache_key)

        if self._redis_enabled and self._redis is not None:
            try:
                split = self._split_cache_key(cache_key)
                pipe = self._redis.pipeline()
                redis_data_key = self._data_key(cache_key)
                pipe.delete(redis_data_key)
                if split:
                    tenant_scope, namespace = split
                    pipe.srem(self._index_key(tenant_scope, namespace), redis_data_key)
                pipe.execute()
            except RedisError as exc:
                self._mark_redis_down(exc)

    def invalidate_namespace(self, namespace: str, *, gym_id: UUID | None = None) -> None:
        tenant_scope = str(gym_id or get_current_gym_id() or "all")
        idx_key = self._index_key(tenant_scope, namespace)

        with self._lock:
            local_keys = self._local_index.pop(idx_key, set())
            for key in local_keys:
                self._local_cache.pop(key, None)

        if self._redis_enabled and self._redis is not None:
            try:
                members = list(self._redis.smembers(idx_key))
                pipe = self._redis.pipeline()
                if members:
                    pipe.delete(*members)
                pipe.delete(idx_key)
                pipe.execute()
            except RedisError as exc:
                self._mark_redis_down(exc)

    def invalidate_namespaces(self, namespaces: Iterable[str], *, gym_id: UUID | None = None) -> None:
        for namespace in set(namespaces):
            self.invalidate_namespace(namespace, gym_id=gym_id)

    def invalidate_by_domains(self, domains: Iterable[str], *, gym_id: UUID | None = None) -> None:
        namespaces = _resolve_namespaces_for_domains(domains)
        if not namespaces:
            return
        self.invalidate_namespaces(namespaces, gym_id=gym_id)

    def healthcheck(self) -> dict[str, object]:
        if not self._redis_configured:
            return {"configured": False, "enabled": False, "available": False, "backend": "memory"}

        if not self._redis_enabled or self._redis is None:
            return {"configured": True, "enabled": False, "available": False, "backend": "memory"}

        try:
            pong = bool(self._redis.ping())
        except RedisError as exc:
            self._mark_redis_down(exc)
            return {"configured": True, "enabled": False, "available": False, "backend": "memory"}

        return {
            "configured": True,
            "enabled": True,
            "available": pong,
            "backend": "redis" if pong else "memory",
        }

    def __contains__(self, cache_key: object) -> bool:
        return isinstance(cache_key, str) and self.get(cache_key) is not None

    def __getitem__(self, cache_key: str) -> object:
        value = self.get(cache_key)
        if value is None:
            raise KeyError(cache_key)
        return value

    def __setitem__(self, cache_key: str, value: object) -> None:
        self.set(cache_key, value)


def _resolve_namespaces_for_domains(domains: Iterable[str]) -> set[str]:
    namespaces: set[str] = set()
    for domain in domains:
        normalized = str(domain).strip().lower()
        if not normalized:
            continue
        if normalized in DASHBOARD_NAMESPACES:
            namespaces.add(normalized)
            continue
        mapped = DASHBOARD_NAMESPACES_BY_DOMAIN.get(normalized)
        if mapped:
            namespaces.update(mapped)
    return namespaces


dashboard_cache = DashboardCache(
    maxsize=settings.dashboard_cache_maxsize,
    default_ttl=settings.dashboard_cache_ttl_seconds,
    redis_url=settings.redis_url,
)


def invalidate_dashboard_cache(*domains: str, gym_id: UUID | None = None) -> None:
    dashboard_cache.invalidate_by_domains(domains, gym_id=gym_id)


def make_cache_key(namespace: str, *parts: object) -> str:
    gym_id = get_current_gym_id()
    tenant_scope = str(gym_id) if gym_id else "all"
    suffix = ":".join(str(part) for part in parts)
    if suffix:
        return f"{tenant_scope}:{namespace}:{suffix}"
    return f"{tenant_scope}:{namespace}"
