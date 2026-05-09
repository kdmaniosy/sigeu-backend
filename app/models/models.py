from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, index=True, nullable=False)
    codigo = Column(String(50), unique=True, nullable=False)
    rol = Column(String(20), nullable=False)  # estudiante, docente, admin
    contrasena = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    reservas = relationship("Reserva", back_populates="usuario")


class Espacio(Base):
    __tablename__ = "espacios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)  # aula, laboratorio
    capacidad = Column(Integer, nullable=False)
    piso = Column(Integer, nullable=False)
    disponible = Column(Boolean, default=True)
    descripcion = Column(Text, nullable=True)
    equipamiento = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    reservas = relationship("Reserva", back_populates="espacio")


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    espacio_id = Column(Integer, ForeignKey("espacios.id"), nullable=False)
    fecha = Column(String(20), nullable=False)
    hora_inicio = Column(String(10), nullable=False)
    hora_fin = Column(String(10), nullable=False)
    motivo = Column(Text, nullable=True)
    estado = Column(String(20), default="Pendiente")  # Pendiente, Confirmada, Cancelada, Completada
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="reservas")
    espacio = relationship("Espacio", back_populates="reservas")