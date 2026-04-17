from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
from fastapi.security import OAuth2PasswordRequestForm
import shutil
import logging
import os

# Importaciones de tus módulos locales
import models, schemas, crud, auth, reportes 
from database import engine, get_db

# 1. CONFIGURACIÓN DE LOGS Y DIRECTORIOS (Original)
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

# 2. MIDDLEWARES (Combinados sin eliminar nada)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Captura de IP para el bloque nuevo
    request.state.ip = request.client.host
    # Log original
    logging.info(f"Ruta accedida: {request.url.path} - Método: {request.method} - IP: {request.state.ip}")
    response = await call_next(request)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Logeamos el error real internamente para el auditor (Original)
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
    # 1. Buscar usuario
    user = db.query(models.Usuario).filter(models.Usuario.correo == form_data.username).first()
    
    # 2. Cambiar status_code a 401 (Estándar de seguridad para que el candado no falle)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=401, 
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"} # Indispensable para Swagger
        )
    
    # 3. CLAVE: Usar .value para que el rol sea un string ('tutor', 'estudiante', etc.)
    access_token = auth.create_access_token(data={
        "sub": user.correo, 
        "rol": user.rol.value if hasattr(user.rol, 'value') else user.rol 
    })
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/usuarios/", response_model=schemas.UsuarioResponse)
def crear_nuevo_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    return crud.crear_usuario(db=db, usuario=usuario)

@app.get("/usuarios/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return crud.obtener_usuarios(db)

# 4. ENDPOINTS DE PRÁCTICAS Y SEGUIMIENTOS
@app.post("/practicas/", response_model=schemas.PracticaResponse)
def iniciar_practica(estudiante_id: str, tutor_id: str, supervisor_id: str, empresa_id: int, db: Session = Depends(get_db)):
    # Nota: se usa str por el cambio a UUID en modelos
    return crud.crear_practica(db, estudiante_id, tutor_id, supervisor_id, empresa_id)

@app.post("/seguimientos/", response_model=schemas.SeguimientoResponse)
def reportar_actividad(
    seguimiento: schemas.SeguimientoCreate, 
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"])) # Blindado original
):
    # Verificación de rol adicional del bloque nuevo
    if current_user.rol != models.UserRole.ESTUDIANTE:
        raise HTTPException(status_code=403, detail="Operación no permitida para su rol")
    return crud.registrar_seguimiento(db=db, seguimiento=seguimiento)

@app.get("/practicas/{practica_id}/seguimientos", response_model=List[schemas.SeguimientoResponse])
def ver_progreso_practica(practica_id: str, db: Session = Depends(get_db)):
    return crud.obtener_seguimientos_practica(db, practica_id=practica_id)

# 5. GESTIÓN DE EVIDENCIAS Y VALIDACIONES (Original completo + Nuevo)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB máximo
ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"]

@app.post("/seguimientos/{id}/subir-evidencia")
async def subir_evidencia(
    id: str, 
    archivo: UploadFile = File(...), 
    db: Session = Depends(get_db),
    user=Depends(auth.verificar_rol(["estudiante"]))
):
    if archivo.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no permitido. Solo se aceptan PDFs, JPG o PNG.")
    
    contents = await archivo.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 5MB.")
    
    ruta_final = f"evidencias/seg_{id}_{archivo.filename}"
    with open(ruta_final, "wb") as buffer:
        buffer.write(contents)
    
    crud.actualizar_evidencia(db, id, ruta_final)
    
    return {
        "message": "Evidencia guardada exitosamente", 
        "ruta": ruta_final,
        "tamaño_kb": len(contents) // 1024
    }

# --- NUEVO ENDPOINT DE VALIDACIÓN POR ESQUEMA (Auditoría) ---
@app.patch("/seguimientos/{id}/validar", response_model=schemas.SeguimientoResponse)
async def validar_seguimiento_endpoint(
    id: str, 
    update_data: schemas.SeguimientoUpdate, 
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    if current_user.rol not in [models.UserRole.TUTOR, models.UserRole.COORDINADOR]:
        raise HTTPException(status_code=403, detail="No tiene permisos de auditoría")
    
    res = crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id, 
        update_data.observaciones_tutor, request.state.ip
    )
    if not res:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return res

# --- ENDPOINTS ORIGINALES DE VALIDACIÓN (Mantenidos) ---
@app.patch("/seguimientos/{seguimiento_id}/validar-tutor", response_model=schemas.SeguimientoResponse)
def aprobar_tutor(
    seguimiento_id: str, 
    db: Session = Depends(get_db), 
    admin=Depends(auth.verificar_rol(["tutor", "coordinador"]))
):
    seguimiento = crud.validar_seguimiento_tutor(db, seguimiento_id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return seguimiento

@app.patch("/seguimientos/{id}/rechazar")
def rechazar(
    id: str, 
    observaciones: str, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["tutor", "supervisor", "coordinador"]))
):
    seguimiento = crud.rechazar_seguimiento(db, id, observaciones)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="No se encontró el registro")
    return {"status": "Rechazado", "observaciones": observaciones}

@app.patch("/seguimientos/{seguimiento_id}/validar-supervisor", response_model=schemas.SeguimientoResponse)
def aprobar_supervisor(
    seguimiento_id: str, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["supervisor", "coordinador"]))
):
    seguimiento = crud.validar_seguimiento_supervisor(db, seguimiento_id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return seguimiento

# 6. REPORTES PDF (Original)
@app.get("/practicas/{practica_id}/reporte-pdf")
def descargar_reporte(practica_id: str, db: Session = Depends(get_db)):
    practica = db.query(models.Practica).filter(models.Practica.id == practica_id).first()
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    
    seguimientos = db.query(models.Seguimiento).filter(models.Seguimiento.practica_id == practica_id).all()
    
    # Aquí estaba el error, asegúrate de pasar solo estos 3 argumentos:
    pdf_buffer = reportes.generar_pdf_practica(
        practica.estudiante.nombre, 
        practica.empresa.nombre if practica.empresa else "Empresa no asignada", 
        seguimientos
    )
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Reporte_SIPRA_{practica_id}.pdf"}
    )


@app.post("/empresas/", response_model=schemas.Empresa) # Asegúrate de tener Empresa en schemas
def crear_empresa(nombre: str, nit: str, direccion: str, db: Session = Depends(get_db)):
    nueva_empresa = models.Empresa(nombre=nombre, nit=nit, direccion=direccion)
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return nueva_empresa
