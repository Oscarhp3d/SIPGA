from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud, auth
from database import get_db

router = APIRouter(prefix="/practicas", tags=["Prácticas"])

@router.post("/", response_model=schemas.PracticaResponse, status_code=status.HTTP_201_CREATED)
def iniciar_practica(
    data: schemas.PracticaCreate, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Inicia una nueva práctica (Solo Coordinadores)."""
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
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Lista todas las prácticas (Solo Coordinadores)."""
    return crud.obtener_todas_practicas(db)

@router.get("/{practica_id}", response_model=schemas.PracticaResponse)
def obtener_practica(
    practica_id: str, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Obtiene los detalles de una práctica (Protección IDOR)."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    
    ids_permitidos = [practica.estudiante_id, practica.tutor_id, practica.supervisor_id]
    if current_user.rol != models.UserRole.coordinador and current_user.id not in ids_permitidos:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta práctica")
        
    return practica

@router.patch("/{practica_id}", response_model=schemas.PracticaResponse)
def actualizar_practica(
    practica_id: str,
    data: schemas.PracticaUpdate,
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Actualiza el estado u otros campos de una práctica (Solo Coordinadores)."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    if data.estado is not None:
        practica.estado = data.estado
    if data.tutor_id is not None:
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
    practica_id: str, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Genera y descarga el reporte PDF de una práctica."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    
    ids_permitidos = [practica.estudiante_id, practica.tutor_id, practica.supervisor_id]
    if current_user.rol != models.UserRole.coordinador and current_user.id not in ids_permitidos:
        raise HTTPException(status_code=403, detail="No tiene permisos para este reporte")

    from reportes import generar_pdf_practica
    from fastapi.responses import StreamingResponse
    
    seguimientos = crud.obtener_seguimientos_practica(db, practica_id=practica_id)
    
    pdf_buffer = generar_pdf_practica(
        practica.estudiante.nombre, 
        practica.empresa.nombre if practica.empresa else "Sin asignar", 
        seguimientos
    )
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Reporte_SIPRA_{practica_id}.pdf"}
    )