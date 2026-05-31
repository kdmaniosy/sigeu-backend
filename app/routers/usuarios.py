from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models.models import User, UserType
from app.dependencies import get_current_user
from app.schemas.schemas import UserRespuesta, UserTypeRespuesta, UserActualizar, UserCrear

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
def actualizar_usuario(
    code: str,
    datos: UserActualizar,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Solo el propio usuario o un admin pueden editar
    if current_user.code != code and current_user.usertype_id != "AD":
        raise HTTPException(status_code=403, detail="No tienes permiso para editar este usuario.")
 
    usuario = db.query(User).filter(User.code == code).first()  # <-- era User.Code (mayuscula), error
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
 
    # Actualizar solo los campos editables
    for key, value in datos.model_dump(exclude_none=True).items():
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

# ─── REGISTRAR ADMIN ────────────────────────────

@router.post("/registrar-admin", response_model=UserRespuesta, status_code=201)
def registrar_admin(
    datos: UserCrear,
    admin_code: str,
    db: Session = Depends(get_db)
):
    # Verificar que quien registra es admin
    admin = db.query(User).filter(
        User.code == admin_code,
        User.usertype_id == "AD"
    ).first()
    if not admin:
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede registrar otros administradores."
        )
    existe = db.query(User).filter(User.email == datos.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    existe_codigo = db.query(User).filter(User.code == datos.code).first()
    if existe_codigo:
        raise HTTPException(status_code=400, detail="El código ya está registrado")
    nuevo = User(
        code=datos.code,
        name1=datos.name1,
        name2=datos.name2,
        last_name1=datos.last_name1,
        last_name2=datos.last_name2,
        email=datos.email,
        cellphone=datos.cellphone,
        usertype_id="AD",
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo