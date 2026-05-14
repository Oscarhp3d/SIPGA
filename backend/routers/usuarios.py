from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

@router.put("/me", response_model=schemas.UsuarioResponse)
def actualizar_mi_perfil(
    usuario: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """Actualiza el perfil del usuario autenticado."""
    if usuario.nombre:
        current_user.nombre = usuario.nombre
    if usuario.correo:
        current_user.correo = usuario.correo
    if usuario.password:
        current_user.password_hash = auth.hash_password(usuario.password)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/{usuario_id}", response_model=schemas.UsuarioResponse)
def actualizar_usuario(
    usuario_id: str,
    usuario: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    db_user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.nombre:
        db_user.nombre = usuario.nombre
    if usuario.correo:
        db_user.correo = usuario.correo
    if usuario.rol:
        db_user.rol = usuario.rol
    if usuario.password:
        db_user.password_hash = auth.hash_password(usuario.password)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Eliminar usuario (Solo Coordinador)."""
    db_user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(db_user)
    db.commit()
    return {"message": "Usuario eliminado correctamente"}