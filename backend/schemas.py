from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Esquemas de Usuario ---
class UsuarioBase(BaseModel):
    nombre: str
    correo: EmailStr
    rol: str # 'estudiante', 'tutor', 'supervisor', 'coordinador'

class UsuarioCreate(UsuarioBase):
    password: str # Solo se recibe al crear, nunca se devuelve en un GET

class UsuarioResponse(UsuarioBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# --- Esquemas de Práctica ---
class PracticaBase(BaseModel):
    estudiante_id: int
    tutor_id: int
    supervisor_id: int
    empresa_nombre: str

# Actualizado: Ahora incluye el campo 'estado' para el frontend
class PracticaResponse(BaseModel):
    id: int
    estudiante_id: int
    tutor_id: int        # Mantenido de tu PracticaBase original
    supervisor_id: int   # Mantenido de tu PracticaBase original
    empresa_nombre: str
    estado: str          # Campo crítico para que el front sepa si está activa/finalizada

    class Config:
        from_attributes = True

# --- Esquemas de Seguimiento (Control de Horas) ---
class SeguimientoBase(BaseModel):
    descripcion: str
    horas_realizadas: float
    fecha_actividad: Optional[datetime] = None

class SeguimientoCreate(SeguimientoBase):
    practica_id: int

class SeguimientoResponse(SeguimientoBase):
    id: int
    validado_tutor: bool
    validado_supervisor: bool

    class Config:
        from_attributes = True

# --- Esquemas de Autenticación (Nuevos) ---
# Estos permiten que el frontend reciba el JWT tras el login exitoso
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
