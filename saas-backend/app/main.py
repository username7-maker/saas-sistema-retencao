from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import Base, engine, SessionLocal
# Importando TODOS os routers
from app.routes import auth, members, tasks, dashboard 
from app.crud import update_all_risk_scores

def daily_risk_job():
    db = SessionLocal()
    try:
        print("--- [JOB] Executando atualização diária ---")
        update_all_risk_scores(db)
    except Exception as e:
        print(f"--- [JOB] ERRO: {e} ---")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_risk_job, 'cron', hour=2, minute=0)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(
    title="AI GYM OS",
    description="Sistema de Gestão de Retenção",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTRO DAS ROTAS (Verifique se todas estão aqui) ---
app.include_router(auth.router)
app.include_router(members.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}