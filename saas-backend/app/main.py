import asyncio
import logging
import time
import uuid as _uuid_mod
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
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
    admin_objections,
    assessments,
    audit,
    auth,
    automations,
    checkins,
    crm,
    dashboards,
    exports,
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
    tasks,
    users,
    whatsapp,
)
from app.core.limiter import RateLimitExceeded, SlowAPIMiddleware, limiter, rate_limit_enabled, rate_limit_exceeded_handler
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

_CRITICAL_API_PREFIXES = (
    f"{settings.api_prefix}/dashboards/action-center",
    f"{settings.api_prefix}/dashboards/retention/queue",
    f"{settings.api_prefix}/roi/summary",
    f"{settings.api_prefix}/imports/assessments",
)


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


@app.middleware("http")
async def critical_endpoint_metrics_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

    if request.url.path.startswith(_CRITICAL_API_PREFIXES):
        logger.info(
            "Critical endpoint served",
            extra={
                "extra_fields": {
                    "event": "critical_endpoint_latency",
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )
    return response


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(members.router, prefix=settings.api_prefix)
app.include_router(assessments.router, prefix=settings.api_prefix)
app.include_router(checkins.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(crm.router, prefix=settings.api_prefix)
app.include_router(nps.router, prefix=settings.api_prefix)
app.include_router(dashboards.router, prefix=settings.api_prefix)
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
app.include_router(whatsapp.router, prefix=settings.api_prefix)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness_check() -> JSONResponse:
    db_status = "ok"
    db_error = ""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)
    finally:
        db.close()

    cache_info = dashboard_cache.healthcheck()
    cache_required = bool(settings.redis_url)
    cache_healthy = (not cache_required) or bool(cache_info.get("available"))
    healthy = db_status == "ok" and cache_healthy
    payload = {
        "status": "ok" if healthy else "degraded",
        "checks": {
            "database": {"status": db_status, "error": db_error},
            "cache": cache_info,
        },
    }
    status_code = 200 if healthy else 503
    return JSONResponse(status_code=status_code, content=payload)


@app.websocket("/ws/updates")
async def updates_websocket(websocket: WebSocket, token: str = Query(...)) -> None:
    try:
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

        await websocket_manager.connect(str(gym_id), websocket)
        await websocket.send_json({"event": "connected", "payload": {"user_id": str(user.id), "gym_id": str(gym_id)}})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websocket_manager.disconnect(str(gym_id), websocket)
    finally:
        clear_current_gym_id()
        db.close()
