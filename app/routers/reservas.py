from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.models import Reserva, Espacio
from app.schemas.schemas import ReservaCrear, ReservaRespuesta

router = APIRouter(prefix="/reservas", tags=["Reservas"])

@router.get("/", response_model=List[ReservaRespuesta])
def obtener_reservas(
    usuario_id: Optional[int] = None,
    espacio_id: Optional[int] = None,
    estado: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reserva)
    if usuario_id:
        query = query.filter(Reserva.usuario_id == usuario_id)
    if espacio_id:
        query = query.filter(Reserva.espacio_id == espacio_id)
    if estado:
        query = query.filter(Reserva.estado == estado)
    if fecha:
        query = query.filter(Reserva.fecha == fecha)
    return query.all()

@router.get("/{reserva_id}", response_model=ReservaRespuesta)
def obtener_reserva(reserva_id: int, db: Session = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva

@router.post("/", response_model=ReservaRespuesta, status_code=201)
def crear_reserva(reserva: ReservaCrear, usuario_id: int, db: Session = Depends(get_db)):
    # Verificar que el espacio existe y está disponible
    espacio = db.query(Espacio).filter(Espacio.id == reserva.espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    if not espacio.disponible:
        raise HTTPException(status_code=400, detail="El espacio no está disponible")
    # Verificar conflicto de horario
    conflicto = db.query(Reserva).filter(
        Reserva.espacio_id == reserva.espacio_id,
        Reserva.fecha == reserva.fecha,
        Reserva.estado != "Cancelada",
        Reserva.hora_inicio < reserva.hora_fin,
        Reserva.hora_fin > reserva.hora_inicio,
    ).first()
    if conflicto:
        raise HTTPException(status_code=400, detail="Ya existe una reserva en ese horario")
    # Crear reserva
    nueva = Reserva(
        usuario_id=usuario_id,
        espacio_id=reserva.espacio_id,
        fecha=reserva.fecha,
        hora_inicio=reserva.hora_inicio,
        hora_fin=reserva.hora_fin,
        motivo=reserva.motivo,
        estado="Pendiente",
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.patch("/{reserva_id}/estado")
def actualizar_estado(reserva_id: int, estado: str, db: Session = Depends(get_db)):
    estados_validos = ["Pendiente", "Confirmada", "Cancelada", "Completada"]
    if estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Usa: {estados_validos}")
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    reserva.estado = estado
    db.commit()
    return {"mensaje": f"Reserva actualizada a {estado}"}

@router.delete("/{reserva_id}")
def cancelar_reserva(reserva_id: int, db: Session = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    reserva.estado = "Cancelada"
    db.commit()
    return {"mensaje": "Reserva cancelada correctamente"}