from sqlalchemy import Column, String, Numeric, Date, ForeignKey, ForeignKeyConstraint, DateTime
from sqlalchemy.orm import relationship
from app.database import Base

# Modelos de la base de datos para el sistema de reservas de espacios universitarios
class UserType(Base):
    __tablename__ = "user_type"
    __table_args__ = {"schema": "sigeu"}

    usertype_id = Column(String(2), primary_key=True)
    name = Column(String(20), nullable=False)

    usuarios = relationship("User", back_populates="tipo_usuario")


# Modelo para representar las ubicaciones de los edificios en la universidad
class Location(Base):
    __tablename__ = "location"
    __table_args__ = {"schema": "sigeu"}

    location_id = Column(String(2), primary_key=True)
    name = Column(String(100), nullable=False)

    edificios = relationship("Building", back_populates="ubicacion")


# Modelo para representar los edificios de la universidad, relacionados con su ubicación
class Building(Base):
    __tablename__ = "building"
    __table_args__ = {"schema": "sigeu"}

    building_id = Column(String(2), primary_key=True)
    name = Column(String(50), nullable=False)
    location_id = Column(String(2), ForeignKey("sigeu.location.location_id"), nullable=False)

    ubicacion = relationship("Location", back_populates="edificios")
    espacios = relationship("Space", back_populates="edificio")


# Modelo para representar los tipos de espacios disponibles en la universidad (aulas, laboratorios, etc.)
class SpaceType(Base):
    __tablename__ = "space_type"
    __table_args__ = {"schema": "sigeu"}

    space_type_id = Column(String(2), primary_key=True)
    name = Column(String(30), nullable=False)

    espacios = relationship("Space", back_populates="tipo_espacio")


# Modelo para representar los espacios físicos de la universidad, relacionados con su edificio y tipo
class Space(Base):
    __tablename__ = "space"
    __table_args__ = {"schema": "sigeu"}

    space_id = Column(String(2), primary_key=True)
    building_id = Column(String(2), ForeignKey("sigeu.building.building_id"), primary_key=True)
    name = Column(String(30), nullable=False)
    capacity = Column(Numeric, nullable=False)
    space_type_id = Column(String(2), ForeignKey("sigeu.space_type.space_type_id"), nullable=False)
    location_id = Column(String(2), nullable=True)

    edificio = relationship("Building", back_populates="espacios")
    tipo_espacio = relationship("SpaceType", back_populates="espacios")


# Modelo para representar los usuarios del sistema, con su información personal y tipo de usuario
class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "sigeu"}

    code = Column(String(10), primary_key=True)
    name1 = Column(String(30), nullable=False)
    name2 = Column(String(30), nullable=True)
    last_name1 = Column(String(30), nullable=False)
    last_name2 = Column(String(30), nullable=True)
    email = Column(String(60), nullable=False)
    cellphone = Column(String(15), nullable=True)
    usertype_id = Column(String(2), ForeignKey("sigeu.user_type.usertype_id"), nullable=False)

    tipo_usuario = relationship("UserType", back_populates="usuarios")
    reservas = relationship("Reservation", back_populates="usuario")


# Modelo para representar las reservas realizadas por los usuarios, con su número de reserva, fecha y usuario asociado
class Reservation(Base):
    __tablename__ = "reservation"
    __table_args__ = {"schema": "sigeu"}

    reservation_number = Column(String(2), primary_key=True)
    date = Column(Date, nullable=False)
    code = Column(String(10), ForeignKey("sigeu.user.code"), nullable=False)

    usuario = relationship("User", back_populates="reservas")
    detalles = relationship("ReservationDetail", back_populates="reserva")


# Modelo para representar los detalles de cada reserva, incluyendo el espacio reservado, horario y estado
class ReservationDetail(Base):
    __tablename__ = "reservation_detail"
    __table_args__ = (
        ForeignKeyConstraint(
            ["reservation_number"],
            ["sigeu.reservation.reservation_number"]
        ),
        {"schema": "sigeu"}
    )

    line_number = Column(Numeric, primary_key=True)
    reservation_number = Column(String(2), primary_key=True)
    space_id = Column(String(2), nullable=False)
    building_id = Column(String(2), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(1), nullable=False)

    reserva = relationship("Reservation", back_populates="detalles")