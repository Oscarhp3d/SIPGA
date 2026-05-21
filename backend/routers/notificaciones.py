from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Notificacion
from schemas import NotificacionResponse
from auth import get_current_user

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

@router.get("/", response_model=List[NotificacionResponse])
def obtener_notificaciones(
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user)
):
    notificaciones = db.query(Notificacion).filter(
        Notificacion.usuario_id == usuario_actual.id
    ).order_by(Notificacion.fecha_creacion.desc()).all()
    return notificaciones

@router.put("/{notificacion_id}/leer", response_model=NotificacionResponse)
def marcar_como_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user)
):
    notificacion = db.query(Notificacion).filter(
        Notificacion.id == notificacion_id,
        Notificacion.usuario_id == usuario_actual.id
    ).first()
    if not notificacion:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    notificacion.leida = True
    db.commit()
    db.refresh(notificacion)
    return notificacion

@router.put("/leer-todas")
def marcar_todas_leidas(
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user)
):
    db.query(Notificacion).filter(
        Notificacion.usuario_id == usuario_actual.id,
        Notificacion.leida == False
    ).update({"leida": True})
    db.commit()
    return {"message": "Todas las notificaciones marcadas como leídas"}
