from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, timezone
from models import UserRole, StatusEnum


class UsuarioBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=150, json_schema_extra={"examples": ["Juan Pérez"]})
    correo: EmailStr = Field(..., max_length=255, json_schema_extra={"examples": ["juan.perez@universidad.edu.co"]})
    rol: UserRole = UserRole.estudiante
    programa_academico: Optional[str] = Field(None, min_length=3, max_length=150, json_schema_extra={"examples": ["Tecnología en Desarrollo de Sistemas"]})

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=64)
    """
    Usado por el coordinador para crear usuarios internamente.
    El consentimiento queda registrado automáticamente en nombre de la institución.
    """

class RegistroPublicoCreate(BaseModel):
    nombre:             str      = Field(..., min_length=3, max_length=150, json_schema_extra={"examples": ["Juan Pérez"]})
    correo:             EmailStr = Field(..., max_length=255, json_schema_extra={"examples": ["juan@universidad.edu.co"]})
    password:           str      = Field(..., min_length=8, max_length=64)
    programa_academico: Optional[str] = Field(None, min_length=3, max_length=150)
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
            raise ValueError("Debe aceptar la política de tratamiento de datos")
        return v

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=150)
    correo: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=64)
    rol: Optional[UserRole] = None
    programa_academico: Optional[str] = Field(None, min_length=3, max_length=150)

class UsuarioResponse(UsuarioBase):
    id:                   str
    fecha_creacion:       datetime
    acepto_politica:      bool
    fecha_consentimiento: Optional[datetime] = None
    version_politica:     Optional[str]      = None
    # Sobreescribe sin min_length para tolerar datos existentes en BD con valor vacío
    programa_academico:   Optional[str]      = Field(None, max_length=150)
    model_config = {"from_attributes": True}


class EmpresaBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=150, json_schema_extra={"examples": ["Tech Solutions S.A.S."]})
    nit: str = Field(..., min_length=5, max_length=20, pattern=r"^[0-9A-Za-z\.-]+$", json_schema_extra={"examples": ["900.123.456-1"]})
    direccion: str = Field(..., min_length=5, max_length=255, json_schema_extra={"examples": ["Calle 100 #15-20"]})

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    model_config = {"from_attributes": True}


class AsignacionTutorCreate(BaseModel):
    tutor_id: str
    programa_academico: str = Field(..., min_length=3, max_length=150, json_schema_extra={"examples": ["Tecnología en Desarrollo de Sistemas"]})

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
    empresa_id: int = Field(..., gt=0)
    horas_totales_requeridas: int = Field(320, gt=0, le=2000)
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

    @model_validator(mode='after')
    def validar_fechas(self):
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValueError("La fecha de fin no puede ser anterior a la fecha de inicio")
        return self

class PracticaCreate(PracticaBase):
    pass

class PracticaUpdate(BaseModel):
    estado: Optional[str] = Field(None, pattern="^(activa|pendiente|finalizada|suspendida)$")
    tutor_id: Optional[str] = None
    supervisor_id: Optional[str] = None
    fecha_fin: Optional[datetime] = None

class PracticaResponse(PracticaBase):
    id: int                          # ← cambiado: str → int
    estado: str
    horas_acumuladas: float = 0.0
    estudiante: Optional[UsuarioResponse] = None
    tutor: Optional[UsuarioResponse] = None
    empresa: Optional[EmpresaResponse] = None
    model_config = {"from_attributes": True}


class SeguimientoBase(BaseModel):
    practica_id: int
    descripcion: str = Field(..., min_length=15, max_length=2000)
    horas_realizadas: float = Field(..., gt=0, le=12)
    fecha_actividad: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('horas_realizadas')
    @classmethod
    def validar_horas(cls, v):
        if v <= 0:
            raise ValueError("Las horas deben ser mayores a cero")
        return v

    @field_validator('fecha_actividad')
    @classmethod
    def validar_fecha(cls, v):
        now = datetime.now(timezone.utc)
        # Normalizar v a timezone-aware si viene sin timezone
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > now:
            raise ValueError("La fecha de la actividad no puede ser futura")
        if v.year != now.year:
            raise ValueError("El año de la actividad debe ser el año actual")
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
    id: int                          # ← cambiado: str → int
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