from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from typing import Optional
from pydantic import BaseModel
from app.database import get_db, Base
from fastapi.responses import StreamingResponse
import threading
import time
from fastapi import Request
from sqlalchemy import func as sql_func

# Router para manejar las operaciones relacionadas con el aforo de los espacios universitarios
router = APIRouter(prefix="/aforo", tags=["Aforo"])


# Modelo para representar los registros de aforo en la base de datos, con información sobre el espacio, edificio, número de personas detectadas y fecha de registro
class AforoRegistro(Base):
    __tablename__ = "aforo"
    __table_args__ = {"schema": "sigeu"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    space_id = Column(String(10), nullable=False)
    building_id = Column(String(10), nullable=False)
    personas_detectadas = Column(Integer, nullable=False)
    registrado_en = Column(DateTime(timezone=True), server_default=func.now())

# Modelos Pydantic para validar la entrada y salida de datos relacionados con el aforo de los espacios universitarios
class AforoInput(BaseModel):
    space_id: str
    building_id: str
    personas_detectadas: int


# Modelo para representar la respuesta al registrar un nuevo aforo, incluyendo el ID del registro, espacio, edificio y número de personas detectadas
class AforoRespuesta(BaseModel):
    id: int
    space_id: str
    building_id: str
    personas_detectadas: int


# Configuración para permitir la creación de instancias de AforoRespuesta a partir de objetos AforoRegistro utilizando from_attributes
    class Config:
        from_attributes = True



# Endpoint para registrar un nuevo aforo en la base de datos, recibiendo los datos a través de un objeto AforoInput y devolviendo la información del registro creado como AforoRespuesta
@router.post("/", response_model=AforoRespuesta, status_code=201)
def registrar_aforo(datos: AforoInput, db: Session = Depends(get_db)):
    registro = AforoRegistro(
        space_id=datos.space_id,
        building_id=datos.building_id,
        personas_detectadas=datos.personas_detectadas,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


# Endpoint para obtener el último registro de aforo de cada espacio, utilizando una subconsulta para obtener la fecha máxima de registro por espacio y edificio, y luego uniendo con la tabla de aforo para obtener los detalles completos de cada registro
@router.get("/actual/todos")
def obtener_aforo_todos_actual(db: Session = Depends(get_db)):
    """
    Devuelve el último registro de aforo de cada espacio en UNA sola consulta.
    """
    subquery = (
        db.query(
            AforoRegistro.space_id,
            AforoRegistro.building_id,
            sql_func.max(AforoRegistro.registrado_en).label("max_fecha")
        )
        .group_by(AforoRegistro.space_id, AforoRegistro.building_id)
        .subquery()
    )

    resultados = (
        db.query(AforoRegistro)
        .join(
            subquery,
            (AforoRegistro.space_id == subquery.c.space_id) &
            (AforoRegistro.building_id == subquery.c.building_id) &
            (AforoRegistro.registrado_en == subquery.c.max_fecha)
        )
        .all()
    )

    return [
        {
            "space_id": r.space_id,
            "building_id": r.building_id,
            "personas_detectadas": r.personas_detectadas,
            "registrado_en": r.registrado_en,
        }
        for r in resultados
    ]


# Endpoint para obtener los últimos 20 registros de aforo, ordenados por fecha de registro en orden descendente
@router.get("/")
def obtener_aforo_todos(db: Session = Depends(get_db)):
    ultimos = db.query(AforoRegistro).order_by(
        AforoRegistro.registrado_en.desc()
    ).limit(20).all()
    return ultimos

# Variable global para el frame compartido
_ultimo_frame: bytes | None = None
_frame_lock = threading.Lock()

def actualizar_frame(frame_bytes: bytes):
    global _ultimo_frame
    with _frame_lock:
        _ultimo_frame = frame_bytes

def generar_stream():
    while True:
        with _frame_lock:
            frame = _ultimo_frame
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.05)
    

# Endpoint para transmitir el video en tiempo real desde el último frame recibido, utilizando StreamingResponse para enviar los datos en formato multipart/x-mixed-replace
@router.get("/stream/{space_id}/{building_id}")
def stream_video(space_id: str, building_id: str):
    return StreamingResponse(
        generar_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# Endpoint para obtener el último registro de aforo de un espacio específico, filtrando por space_id y building_id, y ordenando por fecha de registro en orden descendente para obtener el registro más reciente
@router.get("/{space_id}/{building_id}")
def obtener_aforo_actual(space_id: str, building_id: str, db: Session = Depends(get_db)):
    ultimo = db.query(AforoRegistro).filter(
        AforoRegistro.space_id == space_id,
        AforoRegistro.building_id == building_id,
    ).order_by(AforoRegistro.registrado_en.desc()).first()

    if not ultimo:
        return {"space_id": space_id, "building_id": building_id, "personas_detectadas": 0}

    return {
        "space_id": ultimo.space_id,
        "building_id": ultimo.building_id,
        "personas_detectadas": ultimo.personas_detectadas,
        "registrado_en": ultimo.registrado_en,
    }


# Endpoint para recibir un nuevo frame de video a través de una solicitud POST, actualizando la variable global con el nuevo frame recibido para que pueda ser transmitido a los clientes conectados al endpoint de streaming
@router.post("/frame")
async def recibir_frame(request: Request):
    frame_bytes = await request.body()
    actualizar_frame(frame_bytes)
    return {"ok": True}




