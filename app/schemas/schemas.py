from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ─── USUARIO ───────────────────────────────

class UsuarioBase(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    codigo: str
    rol: str

class UsuarioCrear(UsuarioBase):
    contrasena: str

class UsuarioRespuesta(UsuarioBase):
    id: int
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True

# ─── AUTH ──────────────────────────────────

class Login(BaseModel):
    correo: EmailStr
    contrasena: str

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioRespuesta

# ─── ESPACIO ───────────────────────────────

class EspacioBase(BaseModel):
    nombre: str
    tipo: str
    capacidad: int
    piso: int
    descripcion: Optional[str] = None
    equipamiento: Optional[str] = None

class EspacioCrear(EspacioBase):
    pass

class EspacioRespuesta(EspacioBase):
    id: int
    disponible: bool
    creado_en: datetime

    class Config:
        from_attributes = True

# ─── RESERVA ───────────────────────────────

class ReservaBase(BaseModel):
    espacio_id: int
    fecha: str
    hora_inicio: str
    hora_fin: str
    motivo: Optional[str] = None

class ReservaCrear(ReservaBase):
    pass

class ReservaRespuesta(ReservaBase):
    id: int
    usuario_id: int
    estado: str
    creado_en: datetime
    espacio: EspacioRespuesta

    class Config:
        from_attributes = True