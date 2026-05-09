from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, StatusEnum

# ══════════════════════════════════════════
# USUARIO
# ══════════════════════════════════════════

class UsuarioBase(BaseModel):
    nombre: str = Field(..., example="Juan Pérez")
    correo: EmailStr = Field(..., example="juan.perez@universidad.edu.co")
    rol: UserRole = UserRole.estudiante
    programa_academico: Optional[str] = Field(None, example="Tecnología en Desarrollo de Sistemas")

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8)

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[UserRole] = None
    programa_academico: Optional[str] = None

class UsuarioResponse(UsuarioBase):
    id: str
    fecha_creacion: datetime
    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# EMPRESA
# ══════════════════════════════════════════

class EmpresaBase(BaseModel):
    nombre: str = Field(..., example="Tech Solutions S.A.S.")
    nit: str = Field(..., example="900.123.456-1")
    direccion: str = Field(..., example="Calle 100 #15-20")

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# ASIGNACIÓN TUTOR POR CARRERA
# ══════════════════════════════════════════

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


# ══════════════════════════════════════════
# PRÁCTICA
# ══════════════════════════════════════════

class PracticaBase(BaseModel):
    estudiante_id: str
    # FIX: tutor_id es opcional — el backend lo auto-asigna por programa si no se envía
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
    # Datos anidados opcionales (para el dashboard)
    estudiante: Optional[UsuarioResponse] = None
    tutor: Optional[UsuarioResponse] = None
    empresa: Optional[EmpresaResponse] = None
    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# SEGUIMIENTO
# ══════════════════════════════════════════

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


# ══════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str

class TokenData(BaseModel):
    username: Optional[str] = None
    rol: Optional[str] = None


# ══════════════════════════════════════════
# AUDITORÍA
# ══════════════════════════════════════════

class AuditLogResponse(BaseModel):
    id: int
    usuario_id: Optional[str]
    accion: str
    fecha: datetime
    ip_origen: str
    model_config = {"from_attributes": True}


# ══════════════════════════════════════════
# DASHBOARDS POR ROL
# ══════════════════════════════════════════

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