"""
Router de Dashboard — datos reales desde la base de datos.
Endpoints consumidos directamente por el frontend de SIPRA.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date, timedelta, timezone

import models
import auth
from database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── RESUMEN GENERAL (coordinador) ────────────────────────────────────────────
@router.get("/resumen")
def dashboard_resumen(
    db: Session = Depends(get_db),
    _=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    pasantias_activas = db.query(models.Practica).filter(
        models.Practica.estado == "activa"
    ).count()

    hoy = date.today()
    horas_hoy = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
        func.date(models.Seguimiento.fecha_actividad) == hoy,
        models.Seguimiento.is_deleted == False
    ).scalar() or 0.0

    validaciones_pendientes = db.query(models.Seguimiento).filter(
        models.Seguimiento.is_deleted == False,
        or_(
            models.Seguimiento.estado == models.StatusEnum.enviado,
            models.Seguimiento.estado == models.StatusEnum.pendiente_tutor,
        ),
    ).count()

    return {
        "pasantias_activas": pasantias_activas,
        "horas_hoy": round(horas_hoy, 1),
        "validaciones_pendientes": validaciones_pendientes,
    }


# ── PROGRESO DE PASANTÍAS POR MES (últimos 6 meses) ─────────────────────────
@router.get("/progreso-pasantias")
def progreso_pasantias(
    db: Session = Depends(get_db),
    _=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    hoy = datetime.now(timezone.utc)
    MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    claves_mes = []
    labels = []
    year, month = hoy.year, hoy.month
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        claves_mes.append(f"{y}-{m:02d}")
        labels.append(f"{MESES_ES[m - 1]} {str(y)[2:]}")

    programas: dict = {}
    totales = {c: 0 for c in claves_mes}

    seguimientos = (
        db.query(models.Seguimiento)
        .join(models.Practica, models.Seguimiento.practica_id == models.Practica.id)
        .filter(
            models.Seguimiento.is_deleted == False,
            models.Seguimiento.estado == models.StatusEnum.aprobado,
        )
        .all()
    )

    for s in seguimientos:
        if not s.fecha_actividad:
            continue
        clave = s.fecha_actividad.strftime("%Y-%m")
        if clave not in totales:
            continue
        totales[clave] += 1

        prog = "Sin programa"
        if s.practica and s.practica.estudiante and s.practica.estudiante.programa_academico:
            prog = s.practica.estudiante.programa_academico
        if prog not in programas:
            programas[prog] = {c: 0 for c in claves_mes}
        programas[prog][clave] += 1

    colores = ["#0d1b2e", "#1d4ed8", "#16a34a", "#d97706", "#9333ea", "#ef4444"]
    datasets = []
    for idx, (prog, conteos) in enumerate(programas.items()):
        datasets.append({
            "label": prog[:28],
            "data": [conteos.get(c, 0) for c in claves_mes],
            "backgroundColor": colores[idx % len(colores)],
        })

    if not datasets:
        datasets = [{
            "label": "Horas aprobadas (registros)",
            "data": [totales.get(c, 0) for c in claves_mes],
            "backgroundColor": "#0d1b2e",
        }]

    return {"labels": labels, "datasets": datasets}


# ── ACTIVIDAD RECIENTE ───────────────────────────────────────────────────────
@router.get("/actividad-reciente")
def actividad_reciente(
    db: Session = Depends(get_db),
    _=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    seguimientos = (
        db.query(models.Seguimiento)
        .filter(models.Seguimiento.is_deleted == False)
        .order_by(models.Seguimiento.fecha_actividad.desc())
        .limit(10)
        .all()
    )

    estado_labels = {
        "borrador":  "registró un seguimiento",
        "enviado":   "envió seguimiento para validación",
        "aprobado":  "tiene seguimiento aprobado",
        "rechazado": "tiene seguimiento rechazado",
    }

    actividades = []
    for s in seguimientos:
        practica = s.practica
        nombre = practica.estudiante.nombre if practica and practica.estudiante else "Estudiante"
        empresa = practica.empresa.nombre if practica and practica.empresa else "Empresa"
        estado_val = s.estado.value if hasattr(s.estado, "value") else str(s.estado)
        accion = estado_labels.get(estado_val, "actualizó seguimiento")
        actividades.append({
            "descripcion": f"{nombre} {accion}",
            "empresa": empresa,
            "horas": s.horas_realizadas,
            "estado": s.estado,
            "fecha": s.fecha_actividad.isoformat() if s.fecha_actividad else None,
        })

    return actividades