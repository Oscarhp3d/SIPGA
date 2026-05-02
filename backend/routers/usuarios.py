from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud, auth
from database import get_db

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.post("/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    usuario: schemas.UsuarioCreate, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Crea un nuevo usuario (Solo Coordinadores)."""
    db_user = crud.obtener_usuario_por_correo(db, correo=usuario.correo)
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    return crud.crear_usuario(db=db, usuario=usuario)

@router.get("/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador", "tutor"]))
):
    """Lista todos los usuarios (Solo Coordinadores y Tutores)."""
    return crud.obtener_usuarios(db)

@router.get("/me", response_model=schemas.UsuarioResponse)
def leer_perfil(current_user: models.Usuario = Depends(auth.get_current_user)):
    """Obtiene el perfil del usuario autenticado."""
    return current_user
