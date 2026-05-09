from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, reservas, espacios, usuarios

app = FastAPI(
    title="SIGEU API",
    description="API para el Sistema de Gestión de Espacios Universitarios",
    version="1.0.0"
)

# CORS - permite que el frontend Next.js se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(espacios.router)
app.include_router(reservas.router)
app.include_router(usuarios.router)

@app.get("/")
def raiz():
    return {
        "mensaje": "Bienvenido a la API de SIGEU",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"estado": "ok"}