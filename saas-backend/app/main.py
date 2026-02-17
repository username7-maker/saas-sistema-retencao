from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.background_jobs.scheduler import build_scheduler
from app.core.cache import dashboard_cache
from app.core.config import settings
from app.core.security import decode_token
from app.database import SessionLocal, clear_current_gym_id, set_current_gym_id
from app.models import User
from app.routers import (
    audit,
    auth,
    automations,
    checkins,
    crm,
    dashboards,
    goals,
    imports,
    lgpd,
    members,
    notifications,
    nps,
    reports,
    risk_alerts,
    tasks,
    users,
)
from app.services.websocket_manager import websocket_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    scheduler = None
    if settings.enable_scheduler:
        scheduler = build_scheduler()
        scheduler.start()
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    description="AI GYM OS - BI e Retencao para academias",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    clear_current_gym_id()
    try:
        response = await call_next(request)
        return response
    finally:
        clear_current_gym_id()


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(members.router, prefix=settings.api_prefix)
app.include_router(checkins.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(crm.router, prefix=settings.api_prefix)
app.include_router(nps.router, prefix=settings.api_prefix)
app.include_router(dashboards.router, prefix=settings.api_prefix)
app.include_router(goals.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(lgpd.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(risk_alerts.router, prefix=settings.api_prefix)
app.include_router(automations.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)


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
    healthy = db_status == "ok"
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
