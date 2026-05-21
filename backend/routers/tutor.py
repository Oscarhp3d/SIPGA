
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/tutor", tags=["Tutor"])

solo_tutor = auth.verificar_rol(["tutor", "coordinador"])


@router.get("/dashboard", response_model=schemas.DashboardTutor)
def dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(solo_tutor)
):
    """Dashboard del tutor: estudiantes a cargo, seguimientos pendientes y horas validadas."""
    return crud.dashboard_tutor(db, current_user.id)


@router.get("/mis-estudiantes", response_model=List[schemas.PracticaResponse])
def mis_estudiantes(
    db: Session = Depends(get_db),
    current_user=Depends(solo_tutor)
):
    """Lista las prácticas (con estudiante anidado) que el tutor tiene asignadas."""
    return crud.obtener_practicas_por_usuario(db, current_user.id, "tutor")


@router.get("/pendientes", response_model=List[schemas.SeguimientoResponse])
def seguimientos_pendientes(
    db: Session = Depends(get_db),
    current_user=Depends(solo_tutor)
):
    """Seguimientos en estado 'enviado' que el tutor debe revisar."""
    return crud.obtener_seguimientos_pendientes_tutor(db, current_user.id)


@router.patch("/seguimientos/{id}/validar", response_model=schemas.SeguimientoResponse)
def validar_seguimiento(
    id: int,
    update_data: schemas.SeguimientoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(solo_tutor)
):
    """
    Aprueba o rechaza un seguimiento.
    Solo puede hacerlo si la práctica le pertenece.
    """
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if practica.tutor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Este seguimiento no pertenece a tus estudiantes")

    return crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id,
        update_data.observaciones_tutor or "", request.client.host
    )