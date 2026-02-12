from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from app import crud, schemas, database, models
from ..core.security import get_current_user 

router = APIRouter(prefix="/api/v1/members", tags=["members"])

@router.post("/", response_model=schemas.MemberResponse)
def create_member(
    member: schemas.MemberCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_member(db=db, member=member)

@router.get("/", response_model=List[schemas.MemberResponse])
def list_members(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = Query(None, description="Busca por nome ou e-mail"),
    risk_level: Optional[schemas.RiskLevel] = Query(None, description="Filtrar por nível de risco"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Lista membros com suporte a paginação, busca textual e filtro por nível de risco.
    A ordenação é automática no CRUD: Alunos RED aparecem primeiro.
    """
    return crud.get_members(
        db, 
        skip=skip, 
        limit=limit, 
        search=search, 
        risk_level=risk_level
    )

@router.patch("/{member_id}", response_model=schemas.MemberResponse)
def update_member_details(
    member_id: uuid.UUID,
    member_update: schemas.MemberUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Permite atualizar dados cadastrais do aluno."""
    updated = crud.update_member(db, member_id, member_update)
    if not updated:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return updated

@router.post("/recalculate-risk")
def recalculate_risk(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Dispara a lógica da IA/Regras para atualizar scores de risco e gerar tarefas."""
    return crud.update_all_risk_scores(db)

@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Recebe um arquivo CSV, lê o conteúdo e processa a importação/atualização
    de alunos no banco de dados.
    """
    # Validação simples de extensão
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="O arquivo deve ser um CSV.")
        
    try:
        content = await file.read()
        result = crud.import_members_from_csv(db, content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")