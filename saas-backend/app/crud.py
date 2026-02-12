import csv
import io
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone
from fastapi import HTTPException
from . import models, schemas, core

# --- OPERAÇÕES DE USUÁRIO (AUTENTICAÇÃO) ---

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_pwd = core.security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- OPERAÇÕES DE MEMBROS (AI GYM OS) ---

def create_member(db: Session, member: schemas.MemberCreate):
    existing = db.query(models.Member).filter(models.Member.email == member.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Este e-mail de membro já está cadastrado.")

    member_data = member.model_dump()
    
    if member_data.get("last_checkin") and member_data["last_checkin"].tzinfo:
        member_data["last_checkin"] = member_data["last_checkin"].replace(tzinfo=None)

    db_member = models.Member(**member_data)
    
    if not db_member.id:
        db_member.id = uuid.uuid4()

    try:
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        return db_member
    except Exception as e:
        db.rollback()
        print(f"--- ERRO CRÍTICO NO BANCO ---: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno no banco: {str(e)}")

def get_members(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    search: str = None, 
    risk_level: schemas.RiskLevel = None
):
    query = db.query(models.Member)
    if search:
        query = query.filter(
            (models.Member.name.ilike(f"%{search}%")) | 
            (models.Member.email.ilike(f"%{search}%"))
        )
    if risk_level:
        query = query.filter(models.Member.risk_level == risk_level)
    
    return query.order_by(
        desc(models.Member.risk_level == models.RiskLevel.RED), 
        desc(models.Member.risk_score)
    ).offset(skip).limit(limit).all()

def update_member(db: Session, member_id: uuid.UUID, member_update: schemas.MemberUpdate):
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None
    update_data = member_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    return db_member

# --- OPERAÇÕES DE TAREFAS (TASKS) ---

def create_task(db: Session, task_in: schemas.TaskCreate):
    """
    Cria uma nova tarefa ou registro de atendimento.
    ADICIONADO PARA RESOLVER O ERRO DE ATTRIBUTEERROR
    """
    db_task = models.Task(
        id=uuid.uuid4(),
        member_id=task_in.member_id,
        title="Atendimento Manual", # Título padrão para atendimentos via modal
        description=task_in.description,
        is_completed=True # Marcar como concluído pois é um log de atendimento
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_tasks(db: Session, only_pending: bool = False):
    query = db.query(models.Task)
    if only_pending:
        query = query.filter(models.Task.is_completed == False)
    return query.all()

def update_task(db: Session, task_id: uuid.UUID, task_update: schemas.TaskUpdate):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return None
    
    if task_update.is_completed is not None:
        db_task.is_completed = task_update.is_completed
    if task_update.description:
        db_task.description = f"{db_task.description} | NOTA: {task_update.description}"
        
    db.commit()
    db.refresh(db_task)
    return db_task

# --- LÓGICA DE RISCO E IMPORTAÇÃO ---

def update_all_risk_scores(db: Session):
    members = db.query(models.Member).all()
    today = datetime.now(timezone.utc).date()
    tasks_created = 0
    
    for member in members:
        if member.last_checkin:
            checkin_date = member.last_checkin.date()
            days_inactive = (today - checkin_date).days
            
            if days_inactive > 30:
                member.risk_score = 90
                member.risk_level = models.RiskLevel.RED
            elif days_inactive > 15:
                member.risk_score = 50
                member.risk_level = models.RiskLevel.YELLOW
            else:
                member.risk_score = 10
                member.risk_level = models.RiskLevel.GREEN
        else:
            member.risk_score = 30
            member.risk_level = models.RiskLevel.YELLOW
            
        if member.risk_level == models.RiskLevel.RED:
            existing_task = db.query(models.Task).filter(
                models.Task.member_id == member.id,
                models.Task.is_completed == False
            ).first()
            
            if not existing_task:
                new_task = models.Task(
                    id=uuid.uuid4(),
                    member_id=member.id,
                    title=f"📞 Ligar para {member.name}",
                    description=f"Aluno inativo há mais de 30 dias. Tentar reativação."
                )
                db.add(new_task)
                tasks_created += 1
            
    db.commit()
    return {
        "message": "Processamento concluído com sucesso.",
        "members_analyzed": len(members),
        "new_tasks_created": tasks_created
    }

def import_members_from_csv(db: Session, csv_content: bytes):
    # 1. Decodifica e lê o CSV
    text_data = csv_content.decode("utf-8").strip()
    f = io.StringIO(text_data)
    reader = csv.DictReader(f)
    
    # 2. Limpeza total da base (Rápida)
    try:
        db.query(models.Task).delete()
        db.query(models.Member).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao limpar base antiga")

    new_members_list = [] # Lista para acumular os objetos antes de salvar
    
    for row in reader:
        row_norm = {k.lower().strip(): v for k, v in row.items()}
        
        email = row_norm.get('email') or row_norm.get('e-mail')
        if not email:
            continue

        # Tratamento de Data flexível
        last_checkin_dt = None
        last_checkin_raw = row_norm.get('last_checkin') or row_norm.get('ultimo_checkin')
        if last_checkin_raw:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    last_checkin_dt = datetime.strptime(last_checkin_raw, fmt)
                    break
                except ValueError:
                    continue

        # Em vez de db.add(), criamos o objeto e guardamos na lista
        member = models.Member(
            id=uuid.uuid4(),
            name=row_norm.get('name') or row_norm.get('nome') or "Sem Nome",
            email=email,
            phone=row_norm.get('phone') or row_norm.get('telefone'),
            last_checkin=last_checkin_dt,
            risk_score=0,
            risk_level=models.RiskLevel.GREEN
        )
        new_members_list.append(member)

    # 3. SALVAMENTO EM LOTE (Bulk Insert)
    # Isso é o que permite processar 3.000 alunos em milissegundos
    if new_members_list:
        db.bulk_save_objects(new_members_list)
        db.commit()

    # 4. Atualiza os riscos de toda a nova base
    update_all_risk_scores(db)
    
    return {
        "status": "success", 
        "imported": len(new_members_list),
        "message": f"{len(new_members_list)} alunos importados com alta performance."
    }