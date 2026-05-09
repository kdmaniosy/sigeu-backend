from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Espacio
from app.schemas.schemas import EspacioCrear, EspacioRespuesta

router = APIRouter(prefix="/espacios", tags=["Espacios"])

@router.get("/", response_model=List[EspacioRespuesta])
def obtener_espacios(
    tipo: Optional[str] = None,
    disponible: Optional[bool] = None,
    capacidad_min: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Espacio)
    if tipo:
        query = query.filter(Espacio.tipo == tipo)
    if disponible is not None:
        query = query.filter(Espacio.disponible == disponible)
    if capacidad_min:
        query = query.filter(Espacio.capacidad >= capacidad_min)
    return query.all()

@router.get("/{espacio_id}", response_model=EspacioRespuesta)
def obtener_espacio(espacio_id: int, db: Session = Depends(get_db)):
    espacio = db.query(Espacio).filter(Espacio.id == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return espacio

@router.post("/", response_model=EspacioRespuesta, status_code=201)
def crear_espacio(espacio: EspacioCrear, db: Session = Depends(get_db)):
    nuevo = Espacio(**espacio.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{espacio_id}", response_model=EspacioRespuesta)
def actualizar_espacio(espacio_id: int, datos: EspacioCrear, db: Session = Depends(get_db)):
    espacio = db.query(Espacio).filter(Espacio.id == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    for key, value in datos.model_dump().items():
        setattr(espacio, key, value)
    db.commit()
    db.refresh(espacio)
    return espacio

@router.patch("/{espacio_id}/disponibilidad")
def cambiar_disponibilidad(espacio_id: int, disponible: bool, db: Session = Depends(get_db)):
    espacio = db.query(Espacio).filter(Espacio.id == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    espacio.disponible = disponible
    db.commit()
    return {"mensaje": f"Espacio actualizado a {'disponible' if disponible else 'no disponible'}"}

@router.delete("/{espacio_id}")
def eliminar_espacio(espacio_id: int, db: Session = Depends(get_db)):
    espacio = db.query(Espacio).filter(Espacio.id == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    db.delete(espacio)
    db.commit()
    return {"mensaje": "Espacio eliminado correctamente"}