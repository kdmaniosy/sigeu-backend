from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models.models import User, UserType
from app.schemas.schemas import UserRespuesta, UserTypeRespuesta

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.get("/", response_model=List[UserRespuesta])
def obtener_usuarios(
    usertype_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(User).options(joinedload(User.tipo_usuario))
    if usertype_id:
        query = query.filter(User.USERTYPE_ID == usertype_id)
    return query.all()

@router.get("/{code}", response_model=UserRespuesta)
def obtener_usuario(code: str, db: Session = Depends(get_db)):
    usuario = db.query(User).options(
        joinedload(User.tipo_usuario)
    ).filter(User.Code == code).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.put("/{code}", response_model=UserRespuesta)
def actualizar_usuario(code: str, datos: UserRespuesta, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.Code == code).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for key, value in datos.model_dump(exclude={"tipo_usuario"}).items():
        setattr(usuario, key, value)
    db.commit()
    db.refresh(usuario)
    return usuario

@router.delete("/{code}")
def eliminar_usuario(code: str, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.Code == code).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(usuario)
    db.commit()
    return {"mensaje": "Usuario eliminado correctamente"}

# ─── USER TYPES ────────────────────────────

@router.get("/tipos/all", response_model=List[UserTypeRespuesta])
def obtener_tipos_usuario(db: Session = Depends(get_db)):
    return db.query(UserType).all()