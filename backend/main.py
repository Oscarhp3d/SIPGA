from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import time
import sys
from routers import dashboard


sys.path.append(os.path.dirname(os.path.abspath(__file__)))


import models
from database import engine
from config import settings
from routers import auth_router, usuarios, practicas, seguimientos, empresas, coordinador, tutor, estudiante, supervisor

logging.basicConfig(
    filename='auditoria_sipga.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API profesional para el seguimiento de prácticas profesionales - SIPGA",
    version=settings.VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logging.info(f"Path: {request.url.path} | Method: {request.method} | IP: {request.client.host} | Time: {process_time:.4f}s")
    return response

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


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.include_router(auth_router.router,  prefix=settings.API_V1_STR)
app.include_router(usuarios.router,     prefix=settings.API_V1_STR)
app.include_router(practicas.router,    prefix=settings.API_V1_STR)
app.include_router(seguimientos.router, prefix=settings.API_V1_STR)
app.include_router(empresas.router,     prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
# 7. INCLUSIÓN DE ROUTERS — por rol
app.include_router(coordinador.router,  prefix=settings.API_V1_STR)
app.include_router(tutor.router,        prefix=settings.API_V1_STR)
app.include_router(estudiante.router,   prefix=settings.API_V1_STR)
app.include_router(supervisor.router,   prefix=settings.API_V1_STR)


# 8. SERVIR FRONTEND — Unificación del sistema
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def read_index():
    index_path = os.path.join(frontend_path, "login.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SIPGA API is running. Frontend not found at " + frontend_path}

@app.get("/{page}.html")
def read_page(page: str):
    page_path = os.path.join(frontend_path, f"{page}.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    return JSONResponse(status_code=404, content={"detail": "Page not found"})


os.makedirs(settings.UPLOAD_DIR, exist_ok=True)