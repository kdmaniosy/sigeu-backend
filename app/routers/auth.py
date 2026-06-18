from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.database import get_db
from app.models.models import User
from app.schemas.schemas import Login, Token, UserCrear, UserRespuesta
from app.config import settings
import random
import string
import asyncio
import threading
from datetime import datetime, timedelta
from app.email_service import enviar_email, email_recuperacion
from pydantic import BaseModel, EmailStr


# Router para manejar las operaciones relacionadas con la autenticación de usuarios, incluyendo registro, inicio de sesión y recuperación de contraseña
router = APIRouter(prefix="/auth", tags=["Autenticación"])


# Configuración de PassLib para el manejo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Funciones auxiliares para verificar y hashear contraseñas, así como para crear tokens JWT
def verificar_contrasena(contrasena_plana, contrasena_hash):
    return pwd_context.verify(contrasena_plana, contrasena_hash)

# Función para hashear contraseñas utilizando bcrypt
def hashear_contrasena(contrasena):
    return pwd_context.hash(contrasena)

# Función para crear un token JWT con una fecha de expiración
def crear_token(data: dict):
    datos = data.copy()
    expira = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    datos.update({"exp": expira})
    return jwt.encode(datos, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# Endpoint para registrar un nuevo usuario. Se bloquea el registro directo como administrador y se verifica que el correo y código no estén ya registrados.
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

# Endpoint para iniciar sesión. Se verifica que el correo exista y que la contraseña sea correcta antes de generar un token JWT.
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


# Almacén temporal de códigos de recuperación: { email: (codigo, expiracion) }
codigos_recuperacion: dict[str, tuple[str, datetime]] = {}


# Endpoint para solicitar la recuperación de contraseña. Se genera un código de verificación y se envía por correo al usuario, sin revelar si el correo existe o no.
class RecuperarPasswordRequest(BaseModel):
    email: EmailStr


# Endpoint para verificar el código de recuperación y cambiar la contraseña. Se valida el código, verifica que no haya expirado y actualiza la contraseña del usuario.
class VerificarCodigoRequest(BaseModel):
    email: EmailStr
    codigo: str
    nueva_contrasena: str


# Endpoint para solicitar la recuperación de contraseña. Se genera un código de verificación y se envía por correo al usuario, sin revelar si el correo existe o no.
@router.post("/recuperar-password")
def solicitar_recuperacion(datos: RecuperarPasswordRequest, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.email == datos.email).first()
    if not usuario:
        # No revelamos si el correo existe o no, por seguridad
        return {"mensaje": "Si el correo existe, recibirás un código de verificación."}

    codigo = "".join(random.choices(string.digits, k=6))
    expiracion = datetime.utcnow() + timedelta(minutes=15)
    codigos_recuperacion[datos.email] = (codigo, expiracion)

    try:
        html = email_recuperacion(nombre=usuario.name1, codigo=codigo)

        def enviar_async():
            try:
                asyncio.run(enviar_email(usuario.email, "Código de recuperación - SIGEU", html))
                print(f"✅ Email enviado a {usuario.email}")
            except Exception as ex:
                print(f"❌ Error enviando email: {ex}")

        threading.Thread(target=enviar_async, daemon=True).start()
    except Exception as e:
        print(f"Error preparando email: {e}")

    return {"mensaje": "Si el correo existe, recibirás un código de verificación."}


# Endpoint para verificar el código de recuperación y cambiar la contraseña. Se valida el código, verifica que no haya expirado y actualiza la contraseña del usuario.
@router.post("/verificar-codigo")
def verificar_codigo_y_cambiar(datos: VerificarCodigoRequest, db: Session = Depends(get_db)):
    registro = codigos_recuperacion.get(datos.email)
    if not registro:
        raise HTTPException(status_code=400, detail="No hay una solicitud de recuperación activa para este correo")

    codigo_guardado, expiracion = registro
    if datetime.utcnow() > expiracion:
        del codigos_recuperacion[datos.email]
        raise HTTPException(status_code=400, detail="El código ha expirado. Solicita uno nuevo.")

    if datos.codigo != codigo_guardado:
        raise HTTPException(status_code=400, detail="Código incorrecto")

    usuario = db.query(User).filter(User.email == datos.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.contrasena = hashear_contrasena(datos.nueva_contrasena)
    db.commit()

    del codigos_recuperacion[datos.email]

    return {"mensaje": "Contraseña actualizada correctamente"}