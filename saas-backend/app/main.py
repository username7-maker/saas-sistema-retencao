import asyncio
import json
import logging
import uuid as _uuid_mod
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import urlparse
from uuid import UUID

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.background_jobs.scheduler import build_scheduler, should_start_scheduler_in_api
from app.core.cache import dashboard_cache
from app.core.config import settings
from app.core.logging_config import configure_logging, request_id_ctx
from app.core.security import decode_token
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id

configure_logging()

if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

from app.models import User
from app.routers import (
    actuar_bridge,
    ai_triage,
    admin_objections,
    assessments,
    audit,
    auth,
    automations,
    checkins,
    crm,
    dashboards,
    exports,
    finance,
    goals,
    imports,
    lgpd,
    members,
    notifications,
    nps,
    public,
    reports,
    risk_alerts,
    roi,
    sales,
    settings as settings_router,
    tasks,
    users,
    whatsapp,
)
from app.core.limiter import (
    RateLimitExceeded,
    SlowAPIMiddleware,
    ensure_rate_limiting_ready,
    limiter,
    rate_limit_enabled,
    rate_limit_exceeded_handler,
)
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

AUTH_NO_STORE_PREFIX = f"{settings.api_prefix}/auth"
BASELINE_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
)


ensure_rate_limiting_ready(settings.environment)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    scheduler = None
    websocket_manager.set_event_loop(asyncio.get_running_loop())
    try:
        if should_start_scheduler_in_api():
            logger.info("Scheduler explicitly enabled in API process; starting scheduler in API lifespan.")
            scheduler = build_scheduler()
            scheduler.start()
        else:
            logger.info(
                "Scheduler disabled in API process; keep ENABLE_SCHEDULER=false on the API and run a dedicated worker."
            )
        yield
    finally:
        if scheduler:
            logger.info("Scheduler shutting down in API process.")
            scheduler.shutdown(wait=False)
        websocket_manager.clear_event_loop()


app = FastAPI(
    title=settings.app_name,
    description="AI GYM OS - BI e Retencao para academias",
    version="3.0.0",
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
if rate_limit_enabled:
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_ctx.get("") or str(_uuid_mod.uuid4())[:8]
    logger.exception("Erro nao tratado [%s] %s %s", request_id, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor", "request_id": request_id},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    max_age=3600,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", BASELINE_CONTENT_SECURITY_POLICY)
    if request.url.path.startswith(AUTH_NO_STORE_PREFIX):
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Pragma", "no-cache")
        response.headers.setdefault("Expires", "0")
    if settings.environment.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    return response


@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    clear_current_gym_id()
    try:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            if token:
                try:
                    payload = decode_token(token)
                    gym_id_raw = payload.get("gym_id")
                    if gym_id_raw:
                        set_current_gym_id(UUID(str(gym_id_raw)))
                except Exception:
                    clear_current_gym_id()
        response = await call_next(request)
        return response
    finally:
        clear_current_gym_id()


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Attach a unique request_id to every request for log correlation."""
    rid = request.headers.get("X-Request-ID") or str(_uuid_mod.uuid4())[:8]
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
    finally:
        request_id_ctx.reset(token)


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(members.router, prefix=settings.api_prefix)
app.include_router(assessments.router, prefix=settings.api_prefix)
app.include_router(checkins.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(crm.router, prefix=settings.api_prefix)
app.include_router(nps.router, prefix=settings.api_prefix)
app.include_router(dashboards.router, prefix=settings.api_prefix)
app.include_router(finance.router, prefix=settings.api_prefix)
app.include_router(goals.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(exports.router, prefix=settings.api_prefix)
app.include_router(lgpd.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(risk_alerts.router, prefix=settings.api_prefix)
app.include_router(automations.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(roi.router, prefix=settings.api_prefix)
app.include_router(sales.router, prefix=settings.api_prefix)
app.include_router(public.router, prefix=settings.api_prefix)
app.include_router(admin_objections.router, prefix=settings.api_prefix)
app.include_router(settings_router.router, prefix=settings.api_prefix)
app.include_router(actuar_bridge.router, prefix=settings.api_prefix)
app.include_router(whatsapp.router, prefix=settings.api_prefix)
app.include_router(ai_triage.router, prefix=settings.api_prefix)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check() -> JSONResponse:
    db_status = "ok"
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        logger.warning("Readiness database check failed", exc_info=exc)
    finally:
        db.close()

    cache_info = dashboard_cache.healthcheck()
    cache_required = bool(settings.redis_url)
    cache_healthy = (not cache_required) or bool(cache_info.get("available"))
    cache_status = "ok" if cache_healthy else ("not_configured" if not cache_required else "error")
    healthy = db_status == "ok" and cache_healthy
    payload = {"status": "ok" if healthy else "degraded"}
    if settings.environment.lower() != "production":
        payload["checks"] = {
            "database": {"status": db_status},
            "cache": {"status": cache_status},
        }
    status_code = 200 if healthy else 503
    return JSONResponse(status_code=status_code, content=payload)


def _extract_websocket_auth_token(message: str) -> str | None:
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return None

    if payload.get("type") != "auth":
        return None

    token = payload.get("token")
    if not isinstance(token, str):
        return None

    normalized = token.strip()
    return normalized or None


def _allowed_websocket_origins() -> set[str]:
    allowed = {origin.strip() for origin in settings.cors_origins if origin.strip()}
    frontend_origin = settings.frontend_url.strip()
    if frontend_origin:
        allowed.add(frontend_origin)
    return allowed


def _origin_from_referer(referer: str | None) -> str | None:
    if not referer:
        return None
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _resolve_websocket_origin(websocket: WebSocket) -> str | None:
    origin = (websocket.headers.get("origin") or "").strip()
    if origin:
        return origin
    return _origin_from_referer(websocket.headers.get("referer"))


@app.websocket("/ws/updates")
async def updates_websocket(websocket: WebSocket) -> None:
    if _resolve_websocket_origin(websocket) not in _allowed_websocket_origins():
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        auth_message = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        token = _extract_websocket_auth_token(auth_message)
        if not token:
            await websocket.close(code=4401)
            return

        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4401)
            return
        user_id = UUID(payload["sub"])
        gym_id = UUID(payload["gym_id"])
    except Exception:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        set_current_gym_id(gym_id)
        user = db.get(User, user_id)
        if not user or not user.is_active or user.deleted_at is not None or user.gym_id != gym_id:
            await websocket.close(code=4401)
            return

        await websocket_manager.connect(str(gym_id), websocket, user_id=str(user.id))
        await websocket.send_json({"event": "connected", "payload": {"user_id": str(user.id), "gym_id": str(gym_id)}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websocket_manager.disconnect(str(gym_id), websocket)
    finally:
        clear_current_gym_id()
        db.close()
