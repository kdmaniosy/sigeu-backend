from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models.models import Reservation, ReservationDetail
from app.schemas.schemas import ReservationCrear, ReservationRespuesta, ReservationDetailCrear, ReservationDetailRespuesta

router = APIRouter(prefix="/reservas", tags=["Reservas"])

@router.get("/", response_model=List[ReservationRespuesta])
def obtener_reservas(
    code: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reservation).options(joinedload(Reservation.usuario))
    if code:
        query = query.filter(Reservation.code == code)
    if fecha:
        query = query.filter(Reservation.date == fecha)
    return query.all()

@router.get("/{reservation_number}", response_model=ReservationRespuesta)
def obtener_reserva(reservation_number: str, db: Session = Depends(get_db)):
    reserva = db.query(Reservation).options(
        joinedload(Reservation.usuario),
        joinedload(Reservation.detalles)
    ).filter(Reservation.reservation_number == reservation_number).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva

@router.post("/", response_model=ReservationRespuesta, status_code=201)
def crear_reserva(reserva: ReservationCrear, db: Session = Depends(get_db)):
    existe = db.query(Reservation).filter(
        Reservation.reservation_number == reserva.reservation_number
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="El número de reserva ya existe")
    nueva = Reservation(
        reservation_number=reserva.reservation_number,
        date=reserva.date,
        code=reserva.code,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.delete("/{reservation_number}")
def cancelar_reserva(reservation_number: str, db: Session = Depends(get_db)):
    reserva = db.query(Reservation).filter(
        Reservation.reservation_number == reservation_number
    ).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    db.delete(reserva)
    db.commit()
    return {"mensaje": "Reserva cancelada correctamente"}

# ─── RESERVATION DETAILS ───────────────────

@router.get("/{reservation_number}/detalles", response_model=List[ReservationDetailRespuesta])
def obtener_detalles(reservation_number: str, db: Session = Depends(get_db)):
    return db.query(ReservationDetail).filter(
        ReservationDetail.reservation_number == reservation_number
    ).all()

@router.post("/{reservation_number}/detalles", response_model=ReservationDetailRespuesta, status_code=201)
def agregar_detalle(reservation_number: str, detalle: ReservationDetailCrear, db: Session = Depends(get_db)):
    conflicto = db.query(ReservationDetail).filter(
        ReservationDetail.space_id == detalle.space_id,
        ReservationDetail.building_id == detalle.building_id,
        ReservationDetail.start_time == detalle.start_time,
        ReservationDetail.status != "C",
    ).first()
    if conflicto:
        raise HTTPException(status_code=400, detail="Ya existe una reserva en ese horario para este espacio")
    nuevo_detalle = ReservationDetail(
        line_number=detalle.line_number,
        reservation_number=detalle.reservation_number,
        space_id=detalle.space_id,
        building_id=detalle.building_id,
        start_time=detalle.start_time,
        end_time=detalle.end_time,
        status=detalle.status,
    )
    db.add(nuevo_detalle)
    db.commit()
    db.refresh(nuevo_detalle)
    return nuevo_detalle

@router.patch("/{reservation_number}/detalles/{line_number}/estado")
def actualizar_estado_detalle(reservation_number: str, line_number: float, status: str, db: Session = Depends(get_db)):
    estados_validos = ["A", "C", "P"]
    if status not in estados_validos:
        raise HTTPException(status_code=400, detail="Estado inválido. Usa: A (Activo), C (Cancelado), P (Pendiente)")
    detalle = db.query(ReservationDetail).filter(
        ReservationDetail.reservation_number == reservation_number,
        ReservationDetail.line_number == line_number
    ).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    detalle.status = status
    db.commit()
    return {"mensaje": f"Estado actualizado a {status}"}