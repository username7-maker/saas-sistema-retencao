from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retorna o placar geral da academia (Saúde do Negócio)."""
    
    # Contagens básicas
    total = db.query(models.Member).count()
    active = db.query(models.Member).filter(models.Member.status == models.MemberStatus.ACTIVE).count()
    
    # Distribuição de Risco
    green = db.query(models.Member).filter(models.Member.risk_level == models.RiskLevel.GREEN).count()
    yellow = db.query(models.Member).filter(models.Member.risk_level == models.RiskLevel.YELLOW).count()
    red = db.query(models.Member).filter(models.Member.risk_level == models.RiskLevel.RED).count()
    
    # Tarefas pendentes para a recepção
    tasks = db.query(models.Task).filter(models.Task.is_completed == False).count()

    return {
        "total_members": total,
        "active_members": active,
        "risk_green": green,
        "risk_yellow": yellow,
        "risk_red": red,
        "pending_tasks": tasks
    }