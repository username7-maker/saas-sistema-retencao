from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import models, schemas, database, core

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Cria um novo usuário com senha criptografada."""
    user_exists = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="E-mail já cadastrado."
        )
    
    new_user = models.User(
        email=user_in.email,
        hashed_password=core.security.get_password_hash(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(database.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Autentica o usuário e retorna o Token JWT.
    Nota: form_data.username recebe o e-mail vindo do Swagger.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not core.security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criação do token usando o e-mail como 'sub'
    access_token = core.security.create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }