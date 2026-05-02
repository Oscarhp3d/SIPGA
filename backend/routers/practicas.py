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
    
    # Protección IDOR: Solo el estudiante, tutor, supervisor o coordinador pueden verla
    ids_permitidos = [practica.estudiante_id, practica.tutor_id, practica.supervisor_id]
    if current_user.rol != models.UserRole.COORDINADOR and current_user.id not in ids_permitidos:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta práctica")
        
    return practica

@router.get("/{practica_id}/reporte-pdf")
def descargar_reporte(
    practica_id: str, 
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Genera y descarga el reporte PDF de una prctica."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Prctica no encontrada")
    
    # Seguridad IDOR
    ids_permitidos = [practica.estudiante_id, practica.tutor_id, practica.supervisor_id]
    if current_user.rol != models.UserRole.COORDINADOR and current_user.id not in ids_permitidos:
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

