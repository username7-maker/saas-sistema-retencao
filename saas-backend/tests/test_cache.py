from uuid import uuid4

from app.core.cache import DashboardCache, make_cache_key
from app.database import clear_current_gym_id, set_current_gym_id


def test_make_cache_key_uses_tenant_scope():
    clear_current_gym_id()
    key_without_tenant = make_cache_key("dashboard_executive")
    assert key_without_tenant.startswith("all:dashboard_executive")

    gym_id = uuid4()
    set_current_gym_id(gym_id)
    key_with_tenant = make_cache_key("dashboard_executive", 12)
    assert key_with_tenant == f"{gym_id}:dashboard_executive:12"
    clear_current_gym_id()


def test_local_cache_invalidation_by_namespace_and_tenant():
    cache = DashboardCache(maxsize=16, default_ttl=300, redis_url="")
    gym_id = uuid4()
    other_gym_id = uuid4()

    cache.set(f"{gym_id}:dashboard_executive", {"value": 1})
    cache.set(f"{gym_id}:dashboard_operational", {"value": 2})
    cache.set(f"{other_gym_id}:dashboard_executive", {"value": 3})

    cache.invalidate_namespace("dashboard_executive", gym_id=gym_id)

    assert cache.get(f"{gym_id}:dashboard_executive") is None
    assert cache.get(f"{gym_id}:dashboard_operational") == {"value": 2}
    assert cache.get(f"{other_gym_id}:dashboard_executive") == {"value": 3}


def test_domain_invalidation_targets_expected_dashboards():
    cache = DashboardCache(maxsize=16, default_ttl=300, redis_url="")
    gym_id = uuid4()

    cache.set(f"{gym_id}:dashboard_commercial", {"pipeline": 1})
    cache.set(f"{gym_id}:dashboard_executive", {"total_members": 10})

    cache.invalidate_by_domains(["leads"], gym_id=gym_id)

    assert cache.get(f"{gym_id}:dashboard_commercial") is None
    assert cache.get(f"{gym_id}:dashboard_executive") == {"total_members": 10}


def test_healthcheck_reports_memory_backend_when_redis_not_configured():
    cache = DashboardCache(maxsize=16, default_ttl=300, redis_url="")
    health = cache.healthcheck()
    assert health["configured"] is False
    assert health["backend"] == "memory"
