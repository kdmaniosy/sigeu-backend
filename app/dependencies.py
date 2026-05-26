from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app.models.models import User
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extrae el usuario autenticado desde el JWT.
    Lanza 401 si el token es inválido o el usuario no existe.
    """
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        code: str = payload.get("sub")
        if code is None:
            raise credenciales_exception
    except JWTError:
        raise credenciales_exception

    usuario = db.query(User).filter(User.code == code).first()
    if usuario is None:
        raise credenciales_exception

    return usuario


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Verifica que el usuario autenticado sea administrador (usertype_id == 'AD').
    Lanza 403 si no tiene permisos.
    """
    if current_user.usertype_id != "AD":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return current_user