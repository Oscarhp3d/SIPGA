from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/token", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.Usuario).filter(
        models.Usuario.correo == form_data.username
    ).first()

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"}
        )

    rol = user.rol.value if hasattr(user.rol, 'value') else user.rol
    access_token = auth.create_access_token(data={"sub": user.correo, "rol": rol})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "rol": rol,
        "nombre": user.nombre
    }