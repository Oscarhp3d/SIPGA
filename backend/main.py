from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
import shutil
import os
import logging

# Importaciones de tus módulos locales
import models, schemas, crud, auth, reportes 
from database import engine, get_db

# 1. CONFIGURACIÓN DE LOGS Y DIRECTORIOS
logging.basicConfig(
    filename='auditoria_sipra.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Crear carpeta para evidencias si no existe al arrancar
if not os.path.exists("evidencias"):
    os.makedirs("evidencias")

# Crear tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SIPRA API - Sistema de Prácticas",
    description="API oficial para el seguimiento de prácticas profesionales",
    version="1.1.0",
)

# 2. MIDDLEWARES
@app.middleware("http")
async def log_requests(request, call_next):
    logging.info(f"Ruta accedida: {request.url.path} - Método: {request.method}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Logeamos el error real internamente para el auditor
    logging.error(f"ERROR CRÍTICO: {str(exc)}")
    # Al usuario le damos un mensaje profesional
    return JSONResponse(
        status_code=500,
        content={"message": "Ha ocurrido un error inesperado. Por favor, intente más tarde o contacte al soporte de SIPRA."}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. ENDPOINTS DE USUARIOS Y AUTENTICACIÓN
@app.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.correo == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")
    access_token = auth.create_access_token(data={"sub": user.correo})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/usuarios/", response_model=schemas.UsuarioResponse)
def crear_nuevo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return crud.crear_usuario(db=db, usuario=usuario)

@app.get("/usuarios/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return crud.obtener_usuarios(db)

# 4. ENDPOINTS DE PRÁCTICAS Y SEGUIMIENTOS
@app.post("/practicas/", response_model=schemas.PracticaResponse)
def iniciar_practica(estudiante_id: int, tutor_id: int, supervisor_id: int, empresa: str, db: Session = Depends(get_db)):
    return crud.crear_practica(db, estudiante_id, tutor_id, supervisor_id, empresa)

@app.post("/seguimientos/", response_model=schemas.SeguimientoResponse)
def reportar_actividad(
    seguimiento: schemas.SeguimientoCreate, 
    db: Session = Depends(get_db),
    user=Depends(auth.verificar_rol(["estudiante"])) # Blindado
):
    return crud.registrar_seguimiento(db=db, seguimiento=seguimiento)

@app.get("/practicas/{practica_id}/seguimientos", response_model=List[schemas.SeguimientoResponse])
def ver_progreso_practica(practica_id: int, db: Session = Depends(get_db)):
    return crud.obtener_seguimientos_practica(db, practica_id=practica_id)

# 5. GESTIÓN DE EVIDENCIAS Y VALIDACIONES
# --- CONFIGURACIÓN DE ARCHIVOS ---
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB máximo
ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"]

@app.post("/seguimientos/{id}/subir-evidencia")
async def subir_evidencia(
    id: int, 
    archivo: UploadFile = File(...), 
    db: Session = Depends(get_db),
    user=Depends(auth.verificar_rol(["estudiante"])) # <--- Solo estudiantes
):
    # 1. VALIDACIÓN: Tipo de archivo
    if archivo.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Formato no permitido. Solo se aceptan PDFs, JPG o PNG."
        )
    
    # 2. VALIDACIÓN: Tamaño de archivo
    contents = await archivo.read() # Leemos el contenido para verificar peso
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail="El archivo supera el límite de 5MB."
        )
    
    # 3. GUARDADO FÍSICO
    ruta_final = f"evidencias/seg_{id}_{archivo.filename}"
    
    # IMPORTANTE: Como ya hicimos 'await archivo.read()', el puntero está al final.
    # Escribimos 'contents' directamente en el archivo.
    with open(ruta_final, "wb") as buffer:
        buffer.write(contents)
    
    # 4. ACTUALIZACIÓN EN BASE DE DATOS
    crud.actualizar_evidencia(db, id, ruta_final)
    
    return {
        "message": "Evidencia guardada exitosamente", 
        "ruta": ruta_final,
        "tamaño_kb": len(contents) // 1024
    }


@app.patch("/seguimientos/{seguimiento_id}/validar-tutor", response_model=schemas.SeguimientoResponse)
def aprobar_tutor(
    seguimiento_id: int, 
    db: Session = Depends(get_db), 
    admin=Depends(auth.verificar_rol(["tutor", "coordinador"])) # Blindado
):
    seguimiento = crud.validar_seguimiento_tutor(db, seguimiento_id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return seguimiento

@app.patch("/seguimientos/{id}/rechazar")
def rechazar(
    id: int, 
    observaciones: str, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["tutor", "supervisor", "coordinador"])) # Blindado
):
    seguimiento = crud.rechazar_seguimiento(db, id, observaciones)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="No se encontró el registro")
    return {"status": "Rechazado", "observaciones": observaciones}

@app.patch("/seguimientos/{seguimiento_id}/validar-supervisor", response_model=schemas.SeguimientoResponse)
def aprobar_supervisor(
    seguimiento_id: int, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["supervisor", "coordinador"])) # Recomendado blindar
):
    seguimiento = crud.validar_seguimiento_supervisor(db, seguimiento_id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return seguimiento

# 6. REPORTES PDF
@app.get("/practicas/{practica_id}/reporte-pdf")
def descargar_reporte(practica_id: int, db: Session = Depends(get_db)):
    practica = db.query(models.Practica).filter(models.Practica.id == practica_id).first()
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    
    seguimientos = db.query(models.Seguimiento).filter(models.Seguimiento.practica_id == practica_id).all()
    total_horas = sum(s.horas_realizadas for s in seguimientos)
    
    pdf_buffer = reportes.generar_pdf_practica(
        practica.estudiante.nombre, 
        practica.empresa_nombre, 
        total_horas, 
        seguimientos
    )
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Reporte_SIPRA_{practica_id}.pdf"}
    )
