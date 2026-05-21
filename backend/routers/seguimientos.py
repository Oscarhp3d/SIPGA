from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, status
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
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["estudiante"]))
):
    """Registra un nuevo seguimiento (Solo Estudiantes)."""
    practica = crud.obtener_practica(db, seguimiento.practica_id)
    if not practica or practica.estudiante_id != current_user.id:
        raise HTTPException(status_code=403, detail="No puede reportar en una práctica que no le pertenece")
    return crud.registrar_seguimiento(db=db, seguimiento=seguimiento)


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
    db.commit()
    db.refresh(seg)
    return seg


@router.patch("/{id}/validar", response_model=schemas.SeguimientoResponse)
async def validar_seguimiento(
    id: int,                             # ← int
    update_data: schemas.SeguimientoUpdate,
    request: Request,
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

    return crud.validar_seguimiento(
        db, id, update_data.estado, current_user.id,
        update_data.observaciones_tutor, request.client.host
    )


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