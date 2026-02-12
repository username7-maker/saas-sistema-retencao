from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import uuid
from app.database import get_db
from app import models, schemas, crud
from app.core.security import get_current_user 

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# --- ROTA QUE ESTAVA FALTANDO ---
@router.post("/", response_model=schemas.TaskResponse)
def create_task(
    task_in: schemas.TaskCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Cria uma nova tarefa ou registro de atendimento.
    """
    # Verifica se o membro existe antes de criar a tarefa
    member = db.query(models.Member).filter(models.Member.id == task_in.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    
    return crud.create_task(db=db, task_in=task_in)

# --- SUAS ROTAS ATUAIS ---
@router.get("/", response_model=List[schemas.TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    only_pending: bool = Query(True, description="Filtrar apenas tarefas em aberto")
):
    return crud.get_tasks(db, only_pending=only_pending)

@router.patch("/{task_id}", response_model=schemas.TaskResponse)
def update_task_status(
    task_id: uuid.UUID,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    updated_task = crud.update_task(db, task_id=task_id, task_update=task_update)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return updated_task

@router.get("/stats")
def get_task_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    total = db.query(models.Task).count()
    pending = db.query(models.Task).filter(models.Task.is_completed == False).count()
    completed = total - pending
    
    return {
        "total": total,
        "pending": pending,
        "completed": completed,
        "efficiency_rate": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
    }