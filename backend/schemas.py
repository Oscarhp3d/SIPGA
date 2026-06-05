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
    empresa_id: Optional[int] = Field(None, description="Solo para rol supervisor: empresa que va a supervisar.")
    """
    Usado por el coordinador para crear usuarios internamente.
    El consentimiento queda registrado automáticamente en nombre de la institución.
    Si el rol es supervisor y se envía empresa_id, el vínculo empresa↔supervisor
    se crea automáticamente.
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
    """
    Endpoint público POST /auth/registro.
    El usuario se registra por cuenta propia y DEBE aceptar explícitamente
    la política de tratamiento de datos (Ley 1581/2012 + Decreto 1377/2013).
    """

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
    fecha_inicio_convenio: Optional[datetime] = None
    fecha_fin_convenio: Optional[datetime] = None
    cupos_totales: Optional[int] = 0

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    cupos_ocupados: int = 0
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
    calificacion: float = 0.0
    codigo_certificado: Optional[str] = None
    alerta_progreso: Optional[str] = "ok"
    estudiante: Optional[UsuarioResponse] = None
    tutor: Optional[UsuarioResponse] = None
    empresa: Optional[EmpresaResponse] = None
    model_config = {"from_attributes": True}


class SeguimientoBase(BaseModel):
    practica_id: int
    descripcion: str = Field(..., min_length=15, max_length=2000)
    horas_realizadas: float = Field(..., gt=0, le=8)
    fecha_actividad: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('horas_realizadas')
    @classmethod
    def validar_horas(cls, v):
        if v <= 0 or v > 8:
            raise ValueError("Las horas individuales reportadas deben estar entre 0.1 y 8 horas")
        return v

    @field_validator('fecha_actividad')
    @classmethod
    def validar_fecha(cls, v):
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v > now:
            raise ValueError("La fecha de la actividad no puede ser futura")
        return v

class SeguimientoCreate(SeguimientoBase):
    pass

class SeguimientoUpdate(BaseModel):
    estado: Optional[StatusEnum] = None
    observaciones_tutor: Optional[str] = None
    evidencia_url: Optional[str] = None
    validado_tutor: Optional[bool] = None
    validado_supervisor: Optional[bool] = None
    calificacion_tutor: Optional[float] = None
    calificacion_supervisor: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def map_observaciones(cls, data: any) -> any:
        if isinstance(data, dict):
            if "observaciones" in data and "observaciones_tutor" not in data:
                data["observaciones_tutor"] = data["observaciones"]
        return data

class SeguimientoLoteUpdate(BaseModel):
    ids: List[int]
    estado: StatusEnum
    calificacion: Optional[float] = None
    observaciones: Optional[str] = None

class SeguimientoResponse(SeguimientoBase):
    id: int                          # ← cambiado: str → int
    estado: StatusEnum
    validado_tutor: bool
    validado_supervisor: bool
    observaciones_tutor: Optional[str] = None
    evidencia_url: Optional[str] = None
    archivo_evidencia: Optional[str] = None
    calificacion_tutor: Optional[float] = None
    calificacion_supervisor: Optional[float] = None
    fecha_envio: Optional[datetime] = None
    fecha_preaprobacion: Optional[datetime] = None
    fecha_aprobacion: Optional[datetime] = None
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

class DashboardSupervisor(BaseModel):
    mis_practicantes: List[PracticaResponse]
    seguimientos_pendientes: int
    total_horas_en_practicas: float

class DashboardEstudiante(BaseModel):
    practica: Optional[PracticaResponse]
    horas_hoy: float
    horas_acumuladas: float
    horas_requeridas: int
    porcentaje_avance: float
    seguimientos_recientes: List[SeguimientoResponse]

class NotificacionBase(BaseModel):
    titulo: str = Field(..., max_length=200)
    mensaje: str

class NotificacionCreate(NotificacionBase):
    usuario_id: str

class NotificacionResponse(NotificacionBase):
    id: int
    leida: bool
    fecha_creacion: datetime
    model_config = {"from_attributes": True}


# ── SCHEMAS DE ANALÍTICA PARA EL COORDINADOR ───────────────────

class ProgramMetrics(BaseModel):
    programa: str
    total_estudiantes: int
    total_horas_acumuladas: float
    promedio_horas: float
    promedio_porcentaje_avance: float = 0.0
    estudiantes_completados: int = 0

class PracticanteRanking(BaseModel):
    posicion: int
    estudiante_id: str
    practica_id: int = 0
    nombre: str
    programa: str
    horas_acumuladas: float
    porcentaje_avance: float
    calificacion: float = 0.0
    tasa_rechazo: float = 0.0
    seguimientos_totales: int = 0

class TutorMetrics(BaseModel):
    tutor_id: str
    nombre: str
    estudiantes_asignados: int
    seguimientos_validados: int
    horas_promedio_validadas: float
    seguimientos_rechazados: int = 0

class AnaliticaCoordinadorResponse(BaseModel):
    comparativa_programas: List[ProgramMetrics]
    podio_practicantes: List[PracticanteRanking]
    desempeno_tutores: List[TutorMetrics]
    promedio_horas_preaprobacion: float = 0.0
    promedio_horas_aprobacion: float = 0.0


class EvaluacionPracticaBase(BaseModel):
    practica_id: int
    tipo: str  # "parcial" o "final"
    evaluador_rol: str  # "supervisor" o "tutor"
    calificaciones_items: str  # JSON, ej: {"tecnico": 5, "puntualidad": 4}
    observaciones: Optional[str] = None

class EvaluacionPracticaCreate(EvaluacionPracticaBase):
    pass

class EvaluacionPracticaResponse(EvaluacionPracticaBase):
    id: int
    fecha: datetime
    model_config = {"from_attributes": True}