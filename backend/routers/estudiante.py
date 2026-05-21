from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db
from config import settings
import os

router = APIRouter(prefix="/estudiante", tags=["Estudiante"])

solo_estudiante = auth.verificar_rol(["estudiante"])


@router.get("/dashboard", response_model=schemas.DashboardEstudiante)
def dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(solo_estudiante)
):
    """Dashboard del estudiante: su práctica, horas acumuladas y últimos seguimientos."""
    return crud.dashboard_estudiante(db, current_user.id)


@router.get("/mi-practica", response_model=schemas.PracticaResponse)
def mi_practica(
    db: Session = Depends(get_db),
    current_user=Depends(solo_estudiante)
):
    """Devuelve la práctica activa del estudiante."""
    practicas = crud.obtener_practicas_por_usuario(db, current_user.id, "estudiante")
    if not practicas:
        raise HTTPException(status_code=404, detail="No tienes una práctica registrada aún")
    return practicas[0]


@router.get("/mis-seguimientos", response_model=List[schemas.SeguimientoResponse])
def mis_seguimientos(
    db: Session = Depends(get_db),
    current_user=Depends(solo_estudiante)
):
    """Lista todos los seguimientos del estudiante."""
    practicas = crud.obtener_practicas_por_usuario(db, current_user.id, "estudiante")
    if not practicas:
        return []
    return crud.obtener_seguimientos_practica(db, practicas[0].id)


@router.post("/seguimientos", response_model=schemas.SeguimientoResponse, status_code=201)
def registrar_actividad(
    data: schemas.SeguimientoCreate,
    db: Session = Depends(get_db),
    current_user=Depends(solo_estudiante)
):
    """Registra una nueva actividad/informe de avance."""
    practica = crud.obtener_practica(db, data.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes reportar en esta práctica")
    return crud.registrar_seguimiento(db, data)


@router.post("/seguimientos/{id}/evidencia")
async def subir_evidencia(
    id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(solo_estudiante)
):
    """Adjunta un archivo PDF/imagen como evidencia de un seguimiento."""
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No eres dueño de este seguimiento")

    ALLOWED = {"application/pdf", "image/jpeg", "image/png", "application/octet-stream"}
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    ext_ok = ext in {".pdf", ".jpg", ".jpeg", ".png"}
    if archivo.content_type not in ALLOWED and not ext_ok:
        raise HTTPException(status_code=400, detail="Solo se permiten PDF, JPG o PNG")
    if not ext_ok:
        raise HTTPException(status_code=400, detail="Extensión no permitida. Use .pdf, .jpg o .png")

    contenido = await archivo.read()
    if len(contenido) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera 5MB")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ruta = f"{settings.UPLOAD_DIR}/seg_{id}_{archivo.filename}"
    with open(ruta, "wb") as f:
        f.write(contenido)

    crud.actualizar_evidencia(db, id, ruta)
    return {"message": "Evidencia guardada", "ruta": ruta, "kb": len(contenido) // 1024}