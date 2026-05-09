from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.database import get_db
from app.models.models import Usuario
from app.schemas.schemas import Login, Token, UsuarioCrear, UsuarioRespuesta
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

@router.post("/registro", response_model=UsuarioRespuesta, status_code=201)
def registrar_usuario(usuario: UsuarioCrear, db: Session = Depends(get_db)):
    # Verificar si el correo ya existe
    existe = db.query(Usuario).filter(Usuario.correo == usuario.correo).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    # Verificar si el código ya existe
    existe_codigo = db.query(Usuario).filter(Usuario.codigo == usuario.codigo).first()
    if existe_codigo:
        raise HTTPException(status_code=400, detail="El código ya está registrado")
    # Crear usuario
    nuevo_usuario = Usuario(
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        correo=usuario.correo,
        codigo=usuario.codigo,
        rol=usuario.rol,
        contrasena=hashear_contrasena(usuario.contrasena),
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.post("/login", response_model=Token)
def login(credenciales: Login, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.correo == credenciales.correo).first()
    if not usuario or not verificar_contrasena(credenciales.contrasena, usuario.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not usuario.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    token = crear_token({"sub": str(usuario.id), "rol": usuario.rol})
    return {"access_token": token, "token_type": "bearer", "usuario": usuario}