
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
import schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/supervisor", tags=["Supervisor"])

solo_supervisor = auth.verificar_rol(["supervisor", "coordinador"])


@router.get("/dashboard", response_model=schemas.DashboardSupervisor)
def dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(solo_supervisor)
):
    """Dashboard del supervisor: practicantes, pendientes y horas en prácticas."""
    return crud.dashboard_supervisor(db, current_user.id)


@router.get("/mis-practicantes", response_model=List[schemas.PracticaResponse])
def mis_practicantes(
    db: Session = Depends(get_db),
    current_user=Depends(solo_supervisor)
):
    """Lista las prácticas que el supervisor tiene asignadas."""
    return crud.obtener_practicas_por_usuario(db, current_user.id, "supervisor")


@router.get("/pendientes", response_model=List[schemas.SeguimientoResponse])
def pendientes_validacion(
    db: Session = Depends(get_db),
    current_user=Depends(solo_supervisor)
):
    """Seguimientos enviados que el supervisor debe validar (horas)."""
    return crud.obtener_seguimientos_pendientes_supervisor(db, current_user.id)


@router.patch("/seguimientos/{id}/validar-horas", response_model=schemas.SeguimientoResponse)
def validar_horas(
    id: int,
    update_data: schemas.SeguimientoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(solo_supervisor)
):
    """
    El supervisor aprueba o rechaza las horas de un seguimiento.
    Al aprobar, las horas se suman al acumulado de la práctica.
    """
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="Este practicante no está bajo tu supervisión")

    return crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id,
        update_data.observaciones_tutor or "", request.client.host
    )