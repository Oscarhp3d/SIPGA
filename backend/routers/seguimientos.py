from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import mimetypes
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db
from config import settings

router = APIRouter(prefix="/seguimientos", tags=["Seguimientos"])

@router.post("/", response_model=schemas.SeguimientoResponse, status_code=status.HTTP_201_CREATED)
def reportar_actividad(
    seguimiento: schemas.SeguimientoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Registra un nuevo seguimiento (Solo Estudiantes)."""
    practica = crud.obtener_practica(db, seguimiento.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puede reportar en una práctica que no le pertenece")
    try:
        res = crud.registrar_seguimiento(db=db, seguimiento=seguimiento)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Notificación por correo electrónico real
    try:
        dest_correo = None
        if practica.supervisor_id:
            supervisor = crud.obtener_usuario_por_id(db, practica.supervisor_id)
            if supervisor:
                dest_correo = supervisor.correo
        elif practica.tutor_id:
            tutor = crud.obtener_usuario_por_id(db, practica.tutor_id)
            if tutor:
                dest_correo = tutor.correo

        if dest_correo:
            from email_service import enviar_correo
            asunto = f"SIPGA: Nuevo reporte de seguimiento de {current_user.nombre}"
            cuerpo = (
                f"Estimado tutor/supervisor,\n\n"
                f"El estudiante {current_user.nombre} ha registrado un nuevo informe de avance de prácticas con {res.horas_realizadas:g} horas.\n\n"
                f"Descripción:\n\"{res.descripcion}\"\n\n"
                f"Por favor ingrese a la plataforma SIPGA para realizar la validación correspondiente."
            )
            background_tasks.add_task(enviar_correo, dest_correo, asunto, cuerpo)
    except Exception as e:
        pass

    return res


@router.get("/practica/{practica_id}", response_model=List[schemas.SeguimientoResponse])
def listar_seguimientos_practica(
    practica_id: int,                    # ← int
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    """Lista seguimientos de una práctica (Protección IDOR)."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return crud.obtener_seguimientos_practica(db, practica_id=practica_id)


@router.get("/{id}/evidencia")
def ver_evidencia(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user),
):
    """Descarga/visualiza la evidencia de un seguimiento (estudiante, tutor, supervisor, coordinador)."""
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="No tiene permiso para ver esta evidencia")

    if not crud.seguimiento_tiene_evidencia(seg):
        raise HTTPException(status_code=404, detail="Este seguimiento no tiene evidencia adjunta")

    ruta = crud.obtener_ruta_evidencia_fisica(seg)
    if not ruta:
        raise HTTPException(status_code=404, detail="Archivo de evidencia no encontrado en el servidor")

    media_type, _ = mimetypes.guess_type(ruta)
    nombre = os.path.basename(ruta)
    return FileResponse(
        ruta,
        media_type=media_type or "application/octet-stream",
        filename=nombre,
    )


@router.patch("/{id}/enviar", response_model=schemas.SeguimientoResponse)
def enviar_seguimiento_estudiante(
    id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"])),
):
    """El estudiante envía o reenvía un seguimiento para validación."""
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puede enviar seguimientos de otra práctica")

    if seg.estado not in (models.StatusEnum.borrador, models.StatusEnum.rechazado):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden enviar seguimientos en estado borrador o rechazado",
        )

    seg.estado = models.StatusEnum.enviado
    seg.fecha_envio = models.datetime.datetime.now(models.datetime.timezone.utc)
    db.commit()
    db.refresh(seg)

    # Notificación por correo electrónico real
    try:
        dest_correo = None
        if practica.supervisor_id:
            supervisor = crud.obtener_usuario_por_id(db, practica.supervisor_id)
            if supervisor:
                dest_correo = supervisor.correo
        elif practica.tutor_id:
            tutor = crud.obtener_usuario_por_id(db, practica.tutor_id)
            if tutor:
                dest_correo = tutor.correo

        if dest_correo:
            from email_service import enviar_correo
            asunto = f"SIPGA: Reporte de seguimiento enviado por {current_user.nombre}"
            cuerpo = (
                f"Estimado tutor/supervisor,\n\n"
                f"El estudiante {current_user.nombre} ha enviado para revisión su informe de actividades ({seg.horas_realizadas:g} horas).\n\n"
                f"Por favor ingrese a la plataforma para validar el reporte."
            )
            background_tasks.add_task(enviar_correo, dest_correo, asunto, cuerpo)
    except Exception as e:
        pass

    return seg


@router.patch("/validar-lote", response_model=List[schemas.SeguimientoResponse])
async def validar_seguimientos_lote(
    lote_data: schemas.SeguimientoLoteUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["tutor", "supervisor", "coordinador"]))
):
    """Valida múltiples seguimientos de forma masiva (Tutor, Supervisor, Coordinador)."""
    rol = current_user.rol.value if hasattr(current_user.rol, "value") else current_user.rol
    
    for s_id in lote_data.ids:
        seg = crud.obtener_seguimiento(db, s_id)
        if not seg:
            raise HTTPException(status_code=404, detail=f"Seguimiento ID {s_id} no encontrado")
            
        practica = crud.obtener_practica(db, seg.practica_id)
        if not practica:
            raise HTTPException(status_code=404, detail=f"Práctica para el seguimiento ID {s_id} no encontrada")
            
        if rol == "tutor" and practica.tutor_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"El seguimiento ID {s_id} no pertenece a tus estudiantes")
        if rol == "supervisor" and not crud.usuario_puede_ver_practica(db, current_user, practica):
            raise HTTPException(status_code=403, detail=f"El practicante del seguimiento ID {s_id} no está bajo tu supervisión")

    res = crud.validar_seguimientos_lote(
        db, lote_data.ids, lote_data.estado, current_user.id,
        lote_data.observaciones or "", request.client.host,
        calificacion=lote_data.calificacion
    )
    
    for s in res:
        try:
            practica = crud.obtener_practica(db, s.practica_id)
            estudiante = crud.obtener_usuario_por_id(db, practica.estudiante_id)
            if estudiante:
                from email_service import enviar_correo
                estado_txt = getattr(s.estado, "value", s.estado).upper()
                asunto = f"SIPGA: Tu reporte de seguimiento fue {estado_txt}"
                cuerpo = (
                    f"Hola {estudiante.nombre},\n\n"
                    f"Te informamos que tu reporte de seguimiento de {s.horas_realizadas:g} horas ha sido calificado/cambiado a estado: {estado_txt}.\n\n"
                    f"Observaciones del revisor:\n\"{s.observaciones_tutor or 'Sin observaciones'}\"\n\n"
                    f"Por favor ingresa a la plataforma para ver los detalles."
                )
                background_tasks.add_task(enviar_correo, estudiante.correo, asunto, cuerpo)
        except Exception:
            pass
            
    return res


@router.patch("/{id}/validar", response_model=schemas.SeguimientoResponse)
async def validar_seguimiento(
    id: int,
    update_data: schemas.SeguimientoUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["tutor", "supervisor", "coordinador"]))
):
    """Valida un seguimiento (Tutor, Supervisor, Coordinador)."""
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seg.practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    rol = current_user.rol.value if hasattr(current_user.rol, "value") else current_user.rol
    if rol == "tutor" and practica.tutor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Este seguimiento no pertenece a tus estudiantes")
    if rol == "supervisor" and not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="Este practicante no está bajo tu supervisión")

    res = crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id,
        update_data.observaciones_tutor, request.client.host,
        calificacion_tutor=update_data.calificacion_tutor,
        calificacion_supervisor=update_data.calificacion_supervisor
    )

    # Notificar al estudiante sobre el cambio de estado
    try:
        estudiante = crud.obtener_usuario_por_id(db, practica.estudiante_id)
        if estudiante:
            from email_service import enviar_correo
            estado_txt = getattr(res.estado, "value", res.estado).upper()
            asunto = f"SIPGA: Tu reporte de seguimiento fue {estado_txt}"
            cuerpo = (
                f"Hola {estudiante.nombre},\n\n"
                f"Te informamos que tu reporte de seguimiento de {res.horas_realizadas:g} horas ha sido calificado/cambiado a estado: {estado_txt}.\n\n"
                f"Observaciones del revisor:\n\"{res.observaciones_tutor or 'Sin observaciones'}\"\n\n"
                f"Por favor ingresa a la plataforma para ver los detalles."
            )
            background_tasks.add_task(enviar_correo, estudiante.correo, asunto, cuerpo)
    except Exception as e:
        pass

    return res


@router.post("/{id}/subir-evidencia")
async def subir_evidencia(
    id: int,                             # ← int
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Sube evidencia para un seguimiento (Solo el Estudiante dueño)."""
    seguimiento = crud.obtener_seguimiento(db, id)
    if not seguimiento:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")

    practica = crud.obtener_practica(db, seguimiento.practica_id)
    if practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No es dueño de este seguimiento")

    ALLOWED_TYPES = {
        "application/pdf", "image/jpeg", "image/png",
        "application/octet-stream",
    }
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    ext_ok = ext in {".pdf", ".jpg", ".jpeg", ".png"}
    if archivo.content_type not in ALLOWED_TYPES and not ext_ok:
        raise HTTPException(status_code=400, detail="Formato no permitido. Solo PDFs, JPG o PNG.")
    if not ext_ok:
        raise HTTPException(status_code=400, detail="Extensión no permitida. Use .pdf, .jpg o .png.")

    contents = await archivo.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 5MB.")

    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)

    import uuid
    # Sanitizar y asegurar nombre único
    ext = os.path.splitext(archivo.filename)[1]
    nombre_seguro = f"seg_{id}_{uuid.uuid4().hex}{ext}"
    ruta_final = os.path.join(settings.UPLOAD_DIR, nombre_seguro)
    
    with open(ruta_final, "wb") as buffer:
        buffer.write(contents)

    crud.actualizar_evidencia(db, id, ruta_final)

    return {
        "message": "Evidencia guardada exitosamente",
        "ruta": ruta_final,
        "tamaño_kb": len(contents) // 1024
    }


@router.put("/{id}", response_model=schemas.SeguimientoResponse)
def editar_seguimiento(
    id: int,
    data: schemas.SeguimientoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Permite al estudiante editar un seguimiento en estado borrador o rechazado."""
    seg = crud.obtener_seguimiento(db, id)
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    
    practica = crud.obtener_practica(db, seg.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a este seguimiento")
        
    if seg.estado not in (models.StatusEnum.borrador, models.StatusEnum.rechazado):
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden editar seguimientos en estado borrador o rechazado"
        )
    
    try:
        res = crud.editar_seguimiento(db, id, data.descripcion, data.horas_realizadas, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Notificar al supervisor o tutor sobre el reenvío
    try:
        dest_correo = None
        if practica.supervisor_id:
            supervisor = crud.obtener_usuario_por_id(db, practica.supervisor_id)
            if supervisor:
                dest_correo = supervisor.correo
        elif practica.tutor_id:
            tutor = crud.obtener_usuario_por_id(db, practica.tutor_id)
            if tutor:
                dest_correo = tutor.correo

        if dest_correo:
            from email_service import enviar_correo
            asunto = f"SIPGA: Seguimiento corregido y reenviado por {current_user.nombre}"
            cuerpo = (
                f"Estimado tutor/supervisor,\n\n"
                f"El estudiante {current_user.nombre} ha corregido y reenviado un informe de avance previamente rechazado ({res.horas_realizadas:g} horas).\n\n"
                f"Por favor ingrese al sistema para evaluar la corrección."
            )
            background_tasks.add_task(enviar_correo, dest_correo, asunto, cuerpo)
    except Exception as e:
        pass

    return res