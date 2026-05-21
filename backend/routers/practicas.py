from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, joinedload
from typing import List
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/practicas", tags=["Prácticas"])


@router.post("/", response_model=schemas.PracticaResponse, status_code=status.HTTP_201_CREATED)
def iniciar_practica(
    data: schemas.PracticaCreate,
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """
    Crea una nueva práctica (Solo Coordinadores).
    Si no se envía tutor_id, el backend lo auto-asigna según el programa del estudiante.
    Si tampoco existe asignación automática, la práctica queda sin tutor (se asigna luego).
    """
    estudiante = crud.obtener_usuario_por_id(db, data.estudiante_id)
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if estudiante.rol != models.UserRole.estudiante:
        raise HTTPException(status_code=400, detail="El usuario indicado no tiene rol de estudiante")

    empresa = db.query(models.Empresa).filter(models.Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if data.tutor_id:
        tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
        if not tutor:
            raise HTTPException(status_code=404, detail="Tutor no encontrado")
        if tutor.rol != models.UserRole.tutor:
            raise HTTPException(status_code=400, detail="El usuario indicado no tiene rol de tutor")

    return crud.crear_practica(db, data)


@router.get("/mis", response_model=List[schemas.PracticaResponse])
def mis_practicas(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Obtiene las prácticas del usuario autenticado según su rol."""
    rol = current_user.rol.value if hasattr(current_user.rol, 'value') else current_user.rol
    return crud.obtener_practicas_por_usuario(db, current_user.id, rol)


@router.get("/", response_model=List[schemas.PracticaResponse])
def listar_practicas(
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    """Lista prácticas. Coordinador ve todas; Tutor ve solo las suyas."""
    rol = current_user.rol.value if hasattr(current_user.rol, 'value') else current_user.rol
    if rol == "tutor":
        return crud.obtener_practicas_por_usuario(db, current_user.id, rol)
    return crud.obtener_todas_practicas(db)


@router.get("/{practica_id}", response_model=schemas.PracticaResponse)
def obtener_practica(
    practica_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Obtiene los detalles de una práctica (Protección IDOR)."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="No tiene acceso a esta práctica")

    return practica


@router.patch("/{practica_id}", response_model=schemas.PracticaResponse)
def actualizar_practica(
    practica_id: int,
    data: schemas.PracticaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    """Actualiza el estado u otros campos de una práctica."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if current_user.rol == models.UserRole.tutor:
        if practica.tutor_id != current_user.id:
            raise HTTPException(status_code=403, detail="No puedes modificar una práctica que no te pertenece")
        if data.tutor_id is not None or data.supervisor_id is not None or data.fecha_fin is not None:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar estos campos")
        if data.estado is not None and data.estado != "finalizada":
            raise HTTPException(status_code=403, detail="Solo puedes marcar la práctica como finalizada")

    if data.estado is not None:
        estados_validos = {"activa", "pendiente", "finalizada", "suspendida"}
        if data.estado not in estados_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Estado inválido. Valores permitidos: {', '.join(estados_validos)}"
            )
        practica.estado = data.estado

    if data.tutor_id is not None:
        tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
        if not tutor or tutor.rol != models.UserRole.tutor:
            raise HTTPException(status_code=400, detail="tutor_id inválido o usuario no es tutor")
        practica.tutor_id = data.tutor_id

    if data.supervisor_id is not None:
        practica.supervisor_id = data.supervisor_id

    if data.fecha_fin is not None:
        practica.fecha_fin = data.fecha_fin

    db.commit()
    db.refresh(practica)
    return practica


@router.get("/{practica_id}/reporte-pdf")
def descargar_reporte(
    practica_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Genera y descarga el reporte PDF de una práctica."""
    practica = (
        db.query(models.Practica)
        .options(
            joinedload(models.Practica.estudiante),
            joinedload(models.Practica.empresa),
            joinedload(models.Practica.tutor),
        )
        .filter(models.Practica.id == practica_id)
        .first()
    )
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if not crud.usuario_puede_ver_practica(db, current_user, practica):
        raise HTTPException(status_code=403, detail="No tiene permisos para este reporte")

    from reportes import generar_pdf_practica

    seguimientos = crud.obtener_seguimientos_practica(db, practica_id=practica_id)
    estudiante = practica.estudiante
    programa = getattr(estudiante, "programa_academico", None) if estudiante else None

    pdf_buffer = generar_pdf_practica(
        estudiante.nombre if estudiante else "Estudiante Desconocido",
        practica.empresa.nombre if practica.empresa else "Sin asignar",
        practica.tutor.nombre if practica.tutor else "Sin asignar",
        seguimientos,
        horas_acumuladas=practica.horas_acumuladas or 0.0,
        horas_requeridas=practica.horas_totales_requeridas or 0,
        programa=programa or "",
    )

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="Reporte_SIPGA_{practica_id}.pdf"'
        },
    )

@router.delete("/{practica_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_practica(
    practica_id: int,
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Elimina una práctica y sus seguimientos asociados (Solo Coordinadores)."""
    exito = crud.eliminar_practica(db, practica_id)
    if not exito:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    return None