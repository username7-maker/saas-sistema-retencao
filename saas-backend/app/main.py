from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.background_jobs.scheduler import build_scheduler
from app.core.config import settings
from app.database import engine
from app.models import Base
from app.routers import audit, auth, checkins, crm, dashboards, imports, lgpd, members, nps, tasks, users


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    scheduler = build_scheduler()
    scheduler.start()
    try:
        yield
    finally:
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

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(members.router, prefix=settings.api_prefix)
app.include_router(checkins.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)
app.include_router(crm.router, prefix=settings.api_prefix)
app.include_router(nps.router, prefix=settings.api_prefix)
app.include_router(dashboards.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(lgpd.router, prefix=settings.api_prefix)
app.include_router(audit.router, prefix=settings.api_prefix)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
