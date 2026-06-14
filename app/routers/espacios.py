from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models.models import Space
from app.schemas.schemas import SpaceCrear, SpaceRespuesta

router = APIRouter(prefix="/espacios", tags=["Espacios"])

@router.get("/", response_model=List[SpaceRespuesta])
def obtener_espacios(
    tipo: Optional[str] = None,
    capacidad_min: Optional[float] = None,
    building_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Space).options(
        joinedload(Space.tipo_espacio),
        joinedload(Space.edificio)
    )
    if tipo:
        query = query.filter(Space.space_type_id == tipo)
    if capacidad_min:
        query = query.filter(Space.capacity >= capacidad_min)
    if building_id:
        query = query.filter(Space.building_id == building_id)
    return query.all()

@router.get("/{space_id}/{building_id}", response_model=SpaceRespuesta)
def obtener_espacio(space_id: str, building_id: str, db: Session = Depends(get_db)):
    espacio = db.query(Space).options(
        joinedload(Space.tipo_espacio),
        joinedload(Space.edificio)
    ).filter(
        Space.SPACE_ID == space_id,
        Space.BUILDING_ID == building_id
    ).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return espacio

@router.post("/", response_model=SpaceRespuesta, status_code=201)
def crear_espacio(espacio: SpaceCrear, db: Session = Depends(get_db)):
    nuevo = Space(**espacio.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{space_id}/{building_id}", response_model=SpaceRespuesta)
def actualizar_espacio(space_id: str, building_id: str, datos: SpaceCrear, db: Session = Depends(get_db)):
    espacio = db.query(Space).filter(
        Space.SPACE_ID == space_id,
        Space.BUILDING_ID == building_id
    ).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    for key, value in datos.model_dump().items():
        setattr(espacio, key, value)
    db.commit()
    db.refresh(espacio)
    return espacio

@router.delete("/{space_id}/{building_id}")
def eliminar_espacio(space_id: str, building_id: str, db: Session = Depends(get_db)):
    espacio = db.query(Space).filter(
        Space.SPACE_ID == space_id,
        Space.BUILDING_ID == building_id
    ).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    db.delete(espacio)
    db.commit()
    return {"mensaje": "Espacio eliminado correctamente"}