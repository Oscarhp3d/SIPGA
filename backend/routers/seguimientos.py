from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db
from config import settings
import os

router = APIRouter(prefix="/seguimientos", tags=["Seguimientos"])

@router.post("/", response_model=schemas.SeguimientoResponse)
def reportar_actividad(
    seguimiento: schemas.SeguimientoCreate, 
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Registra un nuevo seguimiento (Solo Estudiantes)."""
    # Verificar que la práctica pertenece al estudiante
    practica = crud.obtener_practica(db, seguimiento.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puede reportar en una práctica que no le pertenece")
    
    return crud.registrar_seguimiento(db=db, seguimiento=seguimiento)

@router.get("/practica/{practica_id}", response_model=List[schemas.SeguimientoResponse])
def listar_seguimientos_practica(
    practica_id: str, 
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    """Lista seguimientos de una práctica (Protección IDOR)."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
        
    ids_permitidos = [practica.estudiante_id, practica.tutor_id, practica.supervisor_id]
    if current_user.rol != models.UserRole.coordinador and current_user.id not in ids_permitidos:
        raise HTTPException(status_code=403, detail="Acceso denegado")
        
    return crud.obtener_seguimientos_practica(db, practica_id=practica_id)

@router.patch("/{id}/validar", response_model=schemas.SeguimientoResponse)
async def validar_seguimiento(
    id: str, 
    update_data: schemas.SeguimientoUpdate, 
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["tutor", "supervisor", "coordinador"]))
):
    """Valida un seguimiento (Tutor, Supervisor, Coordinador)."""
    res = crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id, 
        update_data.observaciones_tutor, request.client.host
    )
    if not res:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return res

@router.post("/{id}/subir-evidencia")
async def subir_evidencia(
    id: str, 
    archivo: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Sube evidencia para un seguimiento (Solo el Estudiante dueño)."""
    seguimiento = crud.obtener_seguimiento(db, id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
        
    # IDOR Protection
    practica = crud.obtener_practica(db, seguimiento.practica_id)
    if practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No es dueño de este seguimiento")

    # Validaciones de archivo
    ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"]
    if archivo.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no permitido. Solo PDFs, JPG o PNG.")
    
    contents = await archivo.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 5MB.")
    
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)
        
    ruta_final = f"{settings.UPLOAD_DIR}/seg_{id}_{archivo.filename}"
    with open(ruta_final, "wb") as buffer:
        buffer.write(contents)
    
    crud.actualizar_evidencia(db, id, ruta_final)
    
    return {
        "message": "Evidencia guardada exitosamente", 
        "ruta": ruta_final,
        "tamaño_kb": len(contents) // 1024
    }