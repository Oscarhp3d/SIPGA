from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, StatusEnum # Importamos los Enums del archivo models

# --- ESQUEMAS DE USUARIO ---
class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: UserRole = UserRole.ESTUDIANTE # Ahora usa el Enum
    programa_academico: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8) # Se mantiene de bloque 2 para seguridad

class UsuarioResponse(UsuarioBase): # Unificado UsuarioResponse y UsuarioOut
    id: str # Cambiado a str para soportar UUID
    fecha_creacion: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- ESQUEMAS DE PRÁCTICA ---
class PracticaBase(BaseModel):
    estudiante_id: str
    tutor_id: str
    supervisor_id: Optional[str] = None
    empresa_id: int
    empresa_nombre: Optional[str] = None

class PracticaResponse(PracticaBase):
    id: str
    estado: str
    horas_totales_requeridas: int = 320
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- ESQUEMAS DE SEGUIMIENTO (El corazón de SIPRA) ---
class SeguimientoBase(BaseModel):
    practica_id: str
    descripcion: str = Field(..., min_length=15)
    horas_realizadas: float = Field(..., gt=0, le=12)
    fecha_actividad: datetime = Field(default_factory=datetime.utcnow)

    @validator('horas_realizadas')
    def validar_horas(cls, v):
        if v <= 0:
            raise ValueError("Las horas deben ser mayores a cero")
        return v

class SeguimientoCreate(SeguimientoBase):
    pass

class SeguimientoUpdate(BaseModel):
    estado: Optional[StatusEnum]
    observaciones_tutor: Optional[str]
    evidencia_url: Optional[str]
    validado_tutor: Optional[bool] = None
    validado_supervisor: Optional[bool] = None

class SeguimientoResponse(SeguimientoBase): # Unificado con SeguimientoOut
    id: str
    estado: StatusEnum
    validado_tutor: bool
    validado_supervisor: bool
    observaciones_tutor: Optional[str] = None
    evidencia_url: Optional[str] = None
    archivo_evidencia: Optional[str] = None

    class Config:
        from_attributes = True

# --- ESQUEMAS DE AUTENTICACIÓN ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- ESQUEMAS DE AUDITORÍA ---
class AuditLogOut(BaseModel):
    id: int
    usuario_id: str
    accion: str
    fecha: datetime
    ip_origen: str
    
    class Config:
        from_attributes = True

# --- ESQUEMA DE EMPRESA (Agrega esto al final de schemas.py) ---
class EmpresaBase(BaseModel):
    nombre: str
    nit: str
    direccion: str

class Empresa(EmpresaBase):
    id: int

    class Config:
        from_attributes = True
