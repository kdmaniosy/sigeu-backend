from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# ─── USER TYPE ─────────────────────────────

class UserTypeBase(BaseModel):
    usertype_id: str
    name: str

class UserTypeRespuesta(UserTypeBase):
    class Config:
        from_attributes = True

# ─── USER ──────────────────────────────────

class UserBase(BaseModel):
    code: str
    name1: str
    name2: Optional[str] = None
    last_name1: str
    last_name2: Optional[str] = None
    email: EmailStr
    cellphone: Optional[str] = None
    usertype_id: str

class UserCrear(UserBase):
    contrasena: str

class UserRespuesta(UserBase):
    tipo_usuario: Optional[UserTypeRespuesta] = None

    class Config:
        from_attributes = True

class UserActualizar(BaseModel):
    name1: str
    name2: Optional[str] = None
    last_name1: str
    last_name2: Optional[str] = None
    email: EmailStr
    cellphone: Optional[str] = None
    usertype_id: str

# ─── AUTH ──────────────────────────────────

class Login(BaseModel):
    email: EmailStr
    contrasena: str

class Token(BaseModel):
    access_token: str
    token_type: str
    usuario: UserRespuesta

# ─── LOCATION ──────────────────────────────

class LocationRespuesta(BaseModel):
    location_id: str
    name: str

    class Config:
        from_attributes = True

# ─── BUILDING ──────────────────────────────

class BuildingRespuesta(BaseModel):
    building_id: str
    name: str
    location_id: str

    class Config:
        from_attributes = True

# ─── SPACE TYPE ────────────────────────────

class SpaceTypeRespuesta(BaseModel):
    space_type_id: str
    name: str

    class Config:
        from_attributes = True

# ─── SPACE ─────────────────────────────────

class SpaceBase(BaseModel):
    space_id: str
    building_id: str
    name: str
    capacity: float
    space_type_id: str

class SpaceCrear(SpaceBase):
    pass

class SpaceRespuesta(SpaceBase):
    tipo_espacio: Optional[SpaceTypeRespuesta] = None
    edificio: Optional[BuildingRespuesta] = None

    class Config:
        from_attributes = True

# ─── RESERVATION DETAIL ────────────────────

class ReservationDetailBase(BaseModel):
    line_number: float
    reservation_number: str
    space_id: str
    building_id: str
    start_time: datetime
    end_time: datetime
    status: str

class ReservationDetailCrear(ReservationDetailBase):
    pass

class ReservationDetailRespuesta(ReservationDetailBase):
    class Config:
        from_attributes = True

# ─── RESERVATION ───────────────────────────

class ReservationBase(BaseModel):
    reservation_number: str
    date: date
    code: str

class ReservationCrear(ReservationBase):
    pass

class ReservationActualizar(BaseModel):
    date: date
    code: str

class ReservationRespuesta(ReservationBase):
    usuario: Optional[UserRespuesta] = None
    detalles: Optional[List[ReservationDetailRespuesta]] = []

    class Config:
        from_attributes = True