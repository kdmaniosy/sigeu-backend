from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from datetime import date, datetime
from app.models.models import Reservation, ReservationDetail, User
from app.schemas.schemas import ReservationCrear, ReservationActualizar, ReservationRespuesta, ReservationDetailCrear, ReservationDetailRespuesta
from app.email_service import enviar_email, email_reserva_creada, email_reserva_cancelada
from app.models.models import User
import asyncio
import threading

from app.database import get_db
from app.models.models import Reservation, ReservationDetail, User
from app.schemas.schemas import (
    ReservationCrear,
    ReservationRespuesta,
    ReservationDetailCrear,
    ReservationDetailRespuesta,
)

router = APIRouter(prefix="/reservas", tags=["Reservas"])

# ─── UTILIDADES ────────────────────────────────────────────────────────────────

def get_reserva_o_404(reservation_number: str, db: Session) -> Reservation:
    """Obtiene una reserva con sus relaciones o lanza 404."""
    reserva = (
        db.query(Reservation)
        .options(joinedload(Reservation.usuario), joinedload(Reservation.detalles))
        .filter(Reservation.reservation_number == reservation_number)
        .first()
    )
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


def validar_disponibilidad(
    db: Session,
    space_id: str,
    building_id: str,
    start_time: datetime,
    end_time: datetime,
    excluir_line_number: Optional[float] = None,
    excluir_reservation_number: Optional[str] = None,
):
    """
    Verifica que no exista otro detalle activo o pendiente que se solape
    con el rango [start_time, end_time] para el mismo espacio/edificio.
    """
    query = db.query(ReservationDetail).filter(
        ReservationDetail.space_id == space_id,
        ReservationDetail.building_id == building_id,
        ReservationDetail.status != "C",          # Ignorar cancelados
        ReservationDetail.start_time < end_time,  # Solapamiento real
        ReservationDetail.end_time > start_time,
    )

    # Al actualizar un detalle existente, excluirlo de la búsqueda de conflictos
    if excluir_line_number is not None and excluir_reservation_number is not None:
        query = query.filter(
            ~and_(
                ReservationDetail.line_number == excluir_line_number,
                ReservationDetail.reservation_number == excluir_reservation_number,
            )
        )

    conflicto = query.first()
    if conflicto:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El espacio '{space_id}' en el edificio '{building_id}' "
                f"ya está reservado entre {conflicto.start_time} y {conflicto.end_time}."
            ),
        )


# ─── RESERVAS ──────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ReservationRespuesta])
def obtener_reservas(
    code: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reservation).options(
        joinedload(Reservation.usuario),
        joinedload(Reservation.detalles)
    )
    if code:
        query = query.filter(Reservation.code == code)
    if fecha:
        query = query.filter(Reservation.date == fecha)
    return query.all()


@router.get("/", response_model=List[ReservationRespuesta])
def obtener_reservas(
    code: Optional[str] = None,
    fecha: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Reservation).options(
        joinedload(Reservation.usuario).joinedload(User.tipo_usuario),
        joinedload(Reservation.detalles)
    )
    if code:
        query = query.filter(Reservation.code == code)
    if fecha:
        query = query.filter(Reservation.date == fecha)
    reservas = query.all()

    # Cargar detalles manualmente si joinedload no los trae
    for reserva in reservas:
        if not reserva.detalles:
            reserva.detalles = db.query(ReservationDetail).filter(
                ReservationDetail.reservation_number == reserva.reservation_number
            ).all()

    return reservas


@router.post("/", response_model=ReservationRespuesta, status_code=201)
def crear_reserva(reserva: ReservationCrear, db: Session = Depends(get_db)):
    """
    Crea una nueva reserva. Verifica que el número de reserva no exista
    y que el usuario (code) exista en el sistema.
    """
    if db.query(Reservation).filter(
        Reservation.reservation_number == reserva.reservation_number
    ).first():
        raise HTTPException(status_code=400, detail="El número de reserva ya existe")

    if not db.query(User).filter(User.code == reserva.code).first():
        raise HTTPException(status_code=404, detail="El usuario con ese código no existe")

    nueva = Reservation(
        reservation_number=reserva.reservation_number,
        date=reserva.date,
        code=reserva.code,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/{reservation_number}", response_model=ReservationRespuesta)
def actualizar_reserva(
    reservation_number: str,
    datos: ReservationActualizar,
    db: Session = Depends(get_db),
):
    reserva = get_reserva_o_404(reservation_number, db)

    if datos.code != reserva.code:
        if not db.query(User).filter(User.code == datos.code).first():
            raise HTTPException(status_code=404, detail="El usuario con ese código no existe")

    reserva.date = datos.date
    reserva.code = datos.code
    db.commit()
    db.refresh(reserva)
    return reserva


@router.delete("/{reservation_number}")
def cancelar_reserva(
    reservation_number: str,
    solicitante_code: str = Query(..., description="Código del usuario que solicita la cancelación"),
    db: Session = Depends(get_db),
):
    """
    Cancela una reserva marcando todos sus detalles como 'C' (Cancelado).
    Solo puede hacerlo:
      - El usuario dueño de la reserva, o
      - Un administrador (usertype_id = 'AD')

    No se elimina el registro físicamente; se mantiene el historial.
    """
    reserva = get_reserva_o_404(reservation_number, db)

    # Verificar que el solicitante existe
    solicitante = db.query(User).filter(User.code == solicitante_code).first()
    if not solicitante:
        raise HTTPException(status_code=404, detail="El usuario solicitante no existe")

    es_admin = solicitante.usertype_id == "AD"
    es_dueno = reserva.code == solicitante_code

    if not es_admin and not es_dueno:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para cancelar esta reserva.",
        )

    # Cancelar todos los detalles activos/pendientes
    detalles_activos = [d for d in reserva.detalles if d.status != "C"]
    if not detalles_activos:
        raise HTTPException(
            status_code=400,
            detail="La reserva ya está completamente cancelada.",
        )

    for detalle in detalles_activos:
        detalle.status = "C"
    
    usuario = db.query(User).filter(User.code == reserva.code).first()
    if usuario:
        try:
            detalle_cancelado = detalles_activos[0]
            html = email_reserva_cancelada(
                nombre=usuario.name1,
                reservation_number=reservation_number,
                espacio=f"{detalle_cancelado.space_id} - {detalle_cancelado.building_id}",
                fecha=str(reserva.date),
            )

            def enviar_async():
                asyncio.run(enviar_email(usuario.email, "Reserva cancelada - SIGEU", html))

            threading.Thread(target=enviar_async, daemon=True).start()
        except Exception as e:
            print(f"Error enviando email: {e}")
    db.commit()
    return {
        "mensaje": f"Reserva '{reservation_number}' cancelada correctamente.",
        "detalles_cancelados": len(detalles_activos),
    }


@router.post("/actualizar-estados")
def actualizar_estados_vencidos(db: Session = Depends(get_db)):
    from datetime import datetime
    ahora = datetime.utcnow()
    detalles_vencidos = db.query(ReservationDetail).filter(
        ReservationDetail.end_time < ahora,
        ReservationDetail.status == "P"
    ).all()
    for detalle in detalles_vencidos:
        detalle.status = "A"
    db.commit()
    return {"mensaje": f"{len(detalles_vencidos)} reservas actualizadas a Completada"}


# ─── RESERVATION DETAILS ───────────────────────────────────────────────────────

@router.get("/{reservation_number}/detalles", response_model=List[ReservationDetailRespuesta])
def obtener_detalles(
    reservation_number: str,
    status: Optional[str] = Query(None, description="Filtrar por estado: A, C o P"),
    db: Session = Depends(get_db),
):
    """Lista los detalles de una reserva, con filtro opcional por estado."""
    get_reserva_o_404(reservation_number, db)  # Valida que la reserva exista

    query = db.query(ReservationDetail).filter(
        ReservationDetail.reservation_number == reservation_number
    )
    if status:
        if status not in ["A", "C", "P"]:
            raise HTTPException(
                status_code=400,
                detail="Estado inválido. Usa: A (Activo), C (Cancelado), P (Pendiente)",
            )
        query = query.filter(ReservationDetail.status == status)

    return query.all()


@router.post("/{reservation_number}/detalles", response_model=ReservationDetailRespuesta, status_code=201)
def agregar_detalle(
    reservation_number: str,
    detalle: ReservationDetailCrear,
    db: Session = Depends(get_db),
):
    """
    Agrega un detalle a una reserva existente.
    Valida solapamiento de horarios para el mismo espacio/edificio.
    """
    reserva = get_reserva_o_404(reservation_number, db)

    if detalle.start_time >= detalle.end_time:
        raise HTTPException(
            status_code=400,
            detail="La hora de inicio debe ser anterior a la hora de fin.",
        )

    validar_disponibilidad(
        db,
        space_id=detalle.space_id,
        building_id=detalle.building_id,
        start_time=detalle.start_time,
        end_time=detalle.end_time,
    )

    nuevo_detalle = ReservationDetail(
        line_number=detalle.line_number,
        reservation_number=reservation_number,
        space_id=detalle.space_id,
        building_id=detalle.building_id,
        start_time=detalle.start_time,
        end_time=detalle.end_time,
        status=detalle.status,
    )
    db.add(nuevo_detalle)
    db.commit()
    db.refresh(nuevo_detalle)

    # Enviar email de confirmación
    usuario = db.query(User).filter(User.code == reserva.code).first()
    if usuario:
        try:
            html = email_reserva_creada(
                nombre=usuario.name1,
                reservation_number=reservation_number,
                espacio=f"{detalle.space_id} - {detalle.building_id}",
                fecha=str(reserva.date),
                hora_inicio=detalle.start_time.strftime("%H:%M"),
                hora_fin=detalle.end_time.strftime("%H:%M"),
            )

            def enviar_async():
                asyncio.run(enviar_email(usuario.email, "Reserva confirmada - SIGEU", html))

            threading.Thread(target=enviar_async, daemon=True).start()
        except Exception as e:
            print(f"Error enviando email: {e}")
        return nuevo_detalle


@router.put("/{reservation_number}/detalles/{line_number}", response_model=ReservationDetailRespuesta)
def actualizar_detalle(
    reservation_number: str,
    line_number: float,
    datos: ReservationDetailCrear,
    db: Session = Depends(get_db),
):
    """
    Actualiza un detalle de reserva (horario, espacio, estado).
    Revalida disponibilidad excluyendo el detalle actual del chequeo.
    """
    detalle = db.query(ReservationDetail).filter(
        ReservationDetail.reservation_number == reservation_number,
        ReservationDetail.line_number == line_number,
    ).first()

    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")

    if detalle.status == "C":
        raise HTTPException(
            status_code=400,
            detail="No se puede modificar un detalle cancelado.",
        )

    if datos.start_time >= datos.end_time:
        raise HTTPException(
            status_code=400,
            detail="La hora de inicio debe ser anterior a la hora de fin.",
        )

    # Validar disponibilidad excluyendo este mismo detalle
    validar_disponibilidad(
        db,
        space_id=datos.space_id,
        building_id=datos.building_id,
        start_time=datos.start_time,
        end_time=datos.end_time,
        excluir_line_number=line_number,
        excluir_reservation_number=reservation_number,
    )

    detalle.space_id = datos.space_id
    detalle.building_id = datos.building_id
    detalle.start_time = datos.start_time
    detalle.end_time = datos.end_time
    detalle.status = datos.status

    db.commit()
    db.refresh(detalle)
    return detalle


@router.patch("/{reservation_number}/detalles/{line_number}/estado")
def actualizar_estado_detalle(
    reservation_number: str,
    line_number: float,
    status: str = Query(..., description="Nuevo estado: A, C o P"),
    db: Session = Depends(get_db),
):
    """Cambia únicamente el estado de un detalle de reserva."""
    if status not in ["A", "C", "P"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Usa: A (Activo), C (Cancelado), P (Pendiente)",
        )

    detalle = db.query(ReservationDetail).filter(
        ReservationDetail.reservation_number == reservation_number,
        ReservationDetail.line_number == line_number,
    ).first()

    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")

    detalle.status = status
    db.commit()
    return {"mensaje": f"Estado actualizado a '{status}'"}