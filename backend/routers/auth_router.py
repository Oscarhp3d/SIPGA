from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import models, schemas, auth, crud
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


@router.post(
    "/registro",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registro público de estudiante",
    description=(
        "Permite que un estudiante se registre por cuenta propia. "
        "**Requiere aceptar explícitamente la política de tratamiento de datos** "
        "(Ley 1581 de 2012 / Decreto 1377 de 2013). "
        "El campo `acepto_politica` debe ser `true`; de lo contrario la solicitud es rechazada con 422."
    ),
)
def registro_publico(
    datos: schemas.RegistroPublicoCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Endpoint abierto (sin autenticación).
    Valida que el usuario haya aceptado la política antes de persistir
    cualquier dato personal — cumplimiento Privacy by Design.
    """
    # Verificar que el correo no esté ya registrado
    if crud.obtener_usuario_por_correo(db, datos.correo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este correo ya está registrado en el sistema.",
        )

    nuevo_usuario = crud.registrar_usuario_publico(db, datos)

    # Registrar el evento en la auditoría
    crud.create_audit_log(
        db,
        usuario_id=nuevo_usuario.id,
        accion=(
            f"REGISTRO_PUBLICO | correo={datos.correo} | "
            f"política={datos.version_politica} | ip={request.client.host}"
        ),
        ip=request.client.host,
    )

    return nuevo_usuario