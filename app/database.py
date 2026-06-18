from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


## ─── CONFIGURACIÓN DE LA BASE DE DATOS ─────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "options": "-c search_path=sigeu"
    },
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True,
)

# Crear una sesión local para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()