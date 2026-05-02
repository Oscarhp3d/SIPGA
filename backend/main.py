from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import time

import sys
import os

# Añadir el directorio actual al path para que los imports funcionen en Render
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importaciones locales
import models
from database import engine
from config import settings
from routers import auth, usuarios, practicas, seguimientos, empresas

# 1. CONFIGURACIÓN DE LOGS
logging.basicConfig(
    filename='auditoria_sipra.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 2. INICIALIZACIÓN DE BASE DE DATOS
# Nota: En producción usar migraciones (Alembic)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API profesional para el seguimiento de prácticas profesionales - SIPRA",
    version=settings.VERSION,
)

# 3. MIDDLEWARES
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Registro de auditoría básico
    client_ip = request.client.host
    logging.info(f"Path: {request.url.path} | Method: {request.method} | IP: {client_ip} | Time: {process_time:.4f}s")
    
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. MANEJO DE EXCEPCIONES GLOBALES
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"ERROR CRÍTICO en {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Ha ocurrido un error interno en el servidor.",
            "error_type": type(exc).__name__
        }
    )

# 5. INCLUSIÓN DE ROUTERS
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(usuarios.router, prefix=settings.API_V1_STR)
app.include_router(practicas.router, prefix=settings.API_V1_STR)
app.include_router(seguimientos.router, prefix=settings.API_V1_STR)
app.include_router(empresas.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "SIPRA API is running",
        "version": settings.VERSION,
        "docs": "/docs"
    }

# Asegurar carpeta de evidencias
if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)
