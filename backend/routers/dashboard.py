"""
Router de Dashboard — datos reales desde la base de datos.
Endpoints consumidos directamente por el frontend de SIPRA.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta

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
        models.Seguimiento.estado == models.StatusEnum.enviado,
        models.Seguimiento.is_deleted == False
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
    hoy = datetime.utcnow()
    meses = []
    for i in range(5, -1, -1):
        primer_dia = (hoy.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        meses.append(primer_dia)

    MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    labels = [MESES_ES[m.month - 1] for m in meses]
    claves_mes = [m.strftime("%Y-%m") for m in meses]

    practicas = db.query(models.Practica).filter(
        models.Practica.fecha_inicio != None
    ).all()

    programas: dict = {}
    totales = {c: 0 for c in claves_mes}

    for p in practicas:
        clave = p.fecha_inicio.strftime("%Y-%m") if p.fecha_inicio else None
        if clave and clave in totales:
            totales[clave] += 1

        if not p.estudiante or not p.estudiante.programa_academico:
            continue
        prog = p.estudiante.programa_academico
        if prog not in programas:
            programas[prog] = {c: 0 for c in claves_mes}
        if clave and clave in programas[prog]:
            programas[prog][clave] += 1

    colores = ["#0d1b2e", "#1d4ed8", "#16a34a", "#d97706", "#9333ea", "#ef4444"]
    datasets = []
    for idx, (prog, conteos) in enumerate(programas.items()):
        datasets.append({
            "label": prog,
            "data": [conteos.get(c, 0) for c in claves_mes],
            "backgroundColor": colores[idx % len(colores)],
        })

    if not datasets:
        datasets = [{
            "label": "Pasantías iniciadas",
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
        accion = estado_labels.get(s.estado, "actualizó seguimiento")
        actividades.append({
            "descripcion": f"{nombre} {accion}",
            "empresa": empresa,
            "horas": s.horas_realizadas,
            "estado": s.estado,
            "fecha": s.fecha_actividad.isoformat() if s.fecha_actividad else None,
        })

    return actividades