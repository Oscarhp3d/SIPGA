"""
Router exclusivo del Coordinador.
Agrupa todas las acciones de gestión que solo el coordinador puede hacer.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/coordinador", tags=["Coordinador"])

solo_coordinador = auth.verificar_rol(["coordinador"])


# ── DASHBOARD ────────────────────────────────────────────────
@router.get("/dashboard", response_model=schemas.DashboardCoordinador)
def dashboard(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Resumen general del sistema: estudiantes, tutores, prácticas y pendientes."""
    return crud.dashboard_coordinador(db)


# ── GESTIÓN DE USUARIOS ──────────────────────────────────────
@router.get("/tutores", response_model=List[schemas.UsuarioResponse])
def listar_tutores(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todos los tutores registrados."""
    return crud.obtener_tutores(db)

@router.get("/estudiantes", response_model=List[schemas.UsuarioResponse])
def listar_estudiantes(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todos los estudiantes registrados."""
    return crud.obtener_estudiantes(db)


# ── ASIGNACIÓN TUTOR → PROGRAMA ACADÉMICO ────────────────────
@router.post("/asignar-tutor", response_model=schemas.AsignacionTutorResponse, status_code=201)
def asignar_tutor_a_programa(
    data: schemas.AsignacionTutorCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(solo_coordinador)
):
    """
    Asigna un tutor a un programa académico completo.
    Todos los estudiantes de ese programa serán atendidos por este tutor.
    Si ya había un tutor asignado al programa, queda inactivo.
    """
    # Validar que el usuario asignado existe y es tutor
    tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    if tutor.rol != models.UserRole.tutor:
        raise HTTPException(status_code=400, detail="El usuario no tiene el rol de tutor")

    asignacion = crud.asignar_tutor_a_programa(db, data)
    crud.create_audit_log(
        db, admin.id,
        f"ASIGNACIÓN: tutor={tutor.nombre} → programa={data.programa_academico}",
        request.client.host
    )
    return asignacion

@router.get("/asignaciones", response_model=List[schemas.AsignacionTutorResponse])
def listar_asignaciones(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todas las asignaciones activas de tutor por programa."""
    return crud.obtener_asignaciones(db)


# ── REASIGNAR TUTOR EN UNA PRÁCTICA ESPECÍFICA ───────────────
@router.patch("/practicas/{practica_id}/reasignar-tutor", response_model=schemas.PracticaResponse)
def reasignar_tutor(
    practica_id: int,
    data: schemas.PracticaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(solo_coordinador)
):
    """
    Cambia el tutor asignado a una práctica individual.
    Útil cuando hay excepciones a la asignación por programa.
    """
    if not data.tutor_id:
        raise HTTPException(status_code=400, detail="Debe enviar el nuevo tutor_id")
    tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
    if not tutor or tutor.rol != models.UserRole.tutor:
        raise HTTPException(status_code=400, detail="tutor_id inválido o usuario no es tutor")

    practica = crud.reasignar_tutor_practica(db, practica_id, data.tutor_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    crud.create_audit_log(
        db, admin.id,
        f"REASIGNACIÓN: práctica={practica_id} → nuevo tutor={tutor.nombre}",
        request.client.host
    )
    return practica


# ── VER SEGUIMIENTOS DE CUALQUIER PRÁCTICA ───────────────────
@router.get("/practicas/{practica_id}/seguimientos", response_model=List[schemas.SeguimientoResponse])
def ver_seguimientos_practica(
    practica_id: int,
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """El coordinador puede ver todos los seguimientos de cualquier práctica."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    return crud.obtener_seguimientos_practica(db, practica_id)