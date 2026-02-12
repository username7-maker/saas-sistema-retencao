import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Configurações básicas
SECRET_KEY = "SUA_CHAVE_SUPER_SECRETA_MUDE_DEPOIS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Define onde o FastAPI deve buscar o token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def get_password_hash(password: str) -> str:
    """Transforma senha plana em Hash seguro."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara senha plana com o Hash do banco."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Gera o Token JWT. 
    'data' deve conter o {'sub': email_do_usuario}
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Valida o token e retorna o email do usuário logado.
    Usado como dependência nas rotas protegidas.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if not email:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception