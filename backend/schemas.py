from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, StatusEnum


class UsuarioBase(BaseModel):
    nombre: str = Field(..., example="Juan Pérez")
    correo: EmailStr = Field(..., example="juan.perez@universidad.edu.co")
    rol: UserRole = UserRole.estudiante
    programa_academico: Optional[str] = Field(None, example="Tecnología en Desarrollo de Sistemas")

class UsuarioCreate(UsuarioBase):
    """
    Usado por el coordinador para crear usuarios internamente.
    El consentimiento queda registrado automáticamente en nombre de la institución.
    """
    password: str = Field(..., min_length=8)


class RegistroPublicoCreate(BaseModel):
    """
    Endpoint público POST /auth/registro.
    El usuario se registra por cuenta propia y DEBE aceptar explícitamente
    la política de tratamiento de datos (Ley 1581/2012 + Decreto 1377/2013).
    """
    nombre:             str      = Field(..., example="Juan Pérez")
    correo:             EmailStr = Field(..., example="juan@universidad.edu.co")
    password:           str      = Field(..., min_length=8)
    programa_academico: Optional[str] = None
    acepto_politica:    bool     = Field(
        ...,
        description="El titular debe aceptar la política de datos (Ley 1581/2012)."
    )
    version_politica:   str      = Field(
        default="v1.0",
        description="Versión del documento de política aceptado."
    )

    @field_validator("acepto_politica")
    @classmethod
    def debe_aceptar(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Debe aceptar la política de tratamiento de datos para registrarse "
                "(Ley 1581 de 2012 / Decreto 1377 de 2013)."
            )
        return v


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[UserRole] = None
    programa_academico: Optional[str] = None

class UsuarioResponse(UsuarioBase):
    id:                   str
    fecha_creacion:       datetime
    acepto_politica:      bool
    fecha_consentimiento: Optional[datetime] = None
    version_politica:     Optional[str]      = None
    model_config = {"from_attributes": True}


class EmpresaBase(BaseModel):
    nombre: str = Field(..., example="Tech Solutions S.A.S.")
    nit: str = Field(..., example="900.123.456-1")
    direccion: str = Field(..., example="Calle 100 #15-20")

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    model_config = {"from_attributes": True}


class AsignacionTutorCreate(BaseModel):
    tutor_id: str
    programa_academico: str = Field(..., example="Tecnología en Desarrollo de Sistemas")

class AsignacionTutorResponse(BaseModel):
    id: int
    tutor_id: str
    programa_academico: str
    fecha_asignacion: datetime
    activa: bool
    tutor: Optional[UsuarioResponse] = None
    model_config = {"from_attributes": True}



class PracticaBase(BaseModel):
    estudiante_id: str
    tutor_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    empresa_id: int
    horas_totales_requeridas: int = 320
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

class PracticaCreate(PracticaBase):
    pass

class PracticaUpdate(BaseModel):
    estado: Optional[str] = None
    tutor_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    fecha_fin: Optional[datetime] = None

class PracticaResponse(PracticaBase):
    id: str
    estado: str
    horas_acumuladas: float = 0.0
    estudiante: Optional[UsuarioResponse] = None
    tutor: Optional[UsuarioResponse] = None
    empresa: Optional[EmpresaResponse] = None
    model_config = {"from_attributes": True}




class SeguimientoBase(BaseModel):
    practica_id: str
    descripcion: str = Field(..., min_length=15)
    horas_realizadas: float = Field(..., gt=0, le=12)
    fecha_actividad: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('horas_realizadas')
    @classmethod
    def validar_horas(cls, v):
        if v <= 0:
            raise ValueError("Las horas deben ser mayores a cero")
        return v

class SeguimientoCreate(SeguimientoBase):
    pass

class SeguimientoUpdate(BaseModel):
    estado: Optional[StatusEnum] = None
    observaciones_tutor: Optional[str] = None
    evidencia_url: Optional[str] = None
    validado_tutor: Optional[bool] = None
    validado_supervisor: Optional[bool] = None

class SeguimientoResponse(SeguimientoBase):
    id: str
    estado: StatusEnum
    validado_tutor: bool
    validado_supervisor: bool
    observaciones_tutor: Optional[str] = None
    evidencia_url: Optional[str] = None
    archivo_evidencia: Optional[str] = None
    model_config = {"from_attributes": True}




class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str

class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None




class AuditLogResponse(BaseModel):
    id: int
    usuario_id: Optional[str]
    accion: str
    fecha: datetime
    ip_origen: str
    model_config = {"from_attributes": True}




class DashboardCoordinador(BaseModel):
    total_estudiantes: int
    total_tutores: int
    total_practicas_activas: int
    practicas_por_programa: dict
    seguimientos_pendientes: int

class DashboardTutor(BaseModel):
    mis_estudiantes: List[PracticaResponse]
    seguimientos_pendientes: int
    total_horas_validadas: float

class DashboardEstudiante(BaseModel):
    practica: Optional[PracticaResponse]
    horas_acumuladas: float
    horas_requeridas: int
    porcentaje_avance: float
    seguimientos_recientes: List[SeguimientoResponse]