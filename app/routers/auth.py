from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import Login, Token, UserCrear, UserRespuesta
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Autenticación"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_contrasena(contrasena_plana, contrasena_hash):
    return pwd_context.verify(contrasena_plana, contrasena_hash)

def hashear_contrasena(contrasena):
    return pwd_context.hash(contrasena)

def crear_token(data: dict):
    datos = data.copy()
    expira = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    datos.update({"exp": expira})
    return jwt.encode(datos, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

@router.post("/registro", response_model=UserRespuesta, status_code=201)
def registrar_usuario(usuario: UserCrear, db: Session = Depends(get_db)):
    # Bloquear registro directo como administrador
    if usuario.usertype_id == "AD":
        raise HTTPException(
            status_code=403,
            detail="No puedes registrarte como administrador. Contacta al administrador del sistema."
        )
    existe = db.query(User).filter(User.email == usuario.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    existe_codigo = db.query(User).filter(User.code == usuario.code).first()
    if existe_codigo:
        raise HTTPException(status_code=400, detail="El código ya está registrado")
    nuevo_usuario = User(
        code=usuario.code,
        name1=usuario.name1,
        name2=usuario.name2,
        last_name1=usuario.last_name1,
        last_name2=usuario.last_name2,
        email=usuario.email,
        cellphone=usuario.cellphone,
        usertype_id=usuario.usertype_id,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.post("/login", response_model=Token)
def login(credenciales: Login, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.email == credenciales.email).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    token = crear_token({"sub": str(usuario.code), "rol": usuario.usertype_id})
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}