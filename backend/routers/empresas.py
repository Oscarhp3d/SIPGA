from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/empresas", tags=["Empresas"])

@router.post("/", response_model=schemas.EmpresaResponse, status_code=status.HTTP_201_CREATED)
def crear_empresa(
    empresa: schemas.EmpresaCreate, 
    db: Session = Depends(get_db),
    admin=Depends(auth.verificar_rol(["coordinador"]))
):
    """Registra una nueva empresa (Solo Coordinadores)."""
    return crud.crear_empresa(db, empresa)

@router.get("/", response_model=List[schemas.EmpresaResponse])
def listar_empresas(
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user)
):
    """Lista todas las empresas registradas."""
    return crud.obtener_empresas(db)