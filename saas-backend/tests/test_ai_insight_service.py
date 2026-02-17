from app.core.cache import make_cache_key
from app.services import ai_insight_service


def test_generate_executive_insight_returns_cached_value(monkeypatch):
    cache_store = {make_cache_key("dashboard_insight_executive"): "insight-cacheado"}

    monkeypatch.setattr(ai_insight_service.dashboard_cache, "get", lambda key: cache_store.get(key))
    monkeypatch.setattr(
        ai_insight_service,
        "_build_executive_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria montar prompt quando ha cache")),
    )

    insight = ai_insight_service.generate_executive_insight(db=None, dashboard_data={})
    assert insight == "insight-cacheado"


def test_generate_retention_insight_returns_cached_value(monkeypatch):
    cache_store = {make_cache_key("dashboard_insight_retention"): "retencao-cacheada"}

    monkeypatch.setattr(ai_insight_service.dashboard_cache, "get", lambda key: cache_store.get(key))
    monkeypatch.setattr(
        ai_insight_service,
        "_fallback_retention_insight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("nao deveria calcular fallback quando ha cache")),
    )

    insight = ai_insight_service.generate_retention_insight(db=None, retention_data={})
    assert insight == "retencao-cacheada"
