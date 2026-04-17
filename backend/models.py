from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import uuid
import enum

# --- ENUMS ---
class UserRole(str, enum.Enum):
    ESTUDIANTE = "estudiante"
    TUTOR = "tutor"
    SUPERVISOR = "supervisor"
    COORDINADOR = "coordinador"

class StatusEnum(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

# --- MODELOS ---

class Usuario(Base):
    __tablename__ = "usuarios"
    # Se usa String con UUID para mayor seguridad
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False) # Mantenido de tu bloque 1
    hashed_password = Column(String, nullable=False)    # Mantenido de tu bloque 2
    rol = Column(Enum(UserRole), default=UserRole.ESTUDIANTE)
    programa_academico = Column(String) 
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), unique=True, index=True, nullable=False)
    nit = Column(String(50), unique=True)
    direccion = Column(String(255))
    
    practicas = relationship("Practica", back_populates="empresa")

class Practica(Base):
    __tablename__ = "practicas"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    estudiante_id = Column(String, ForeignKey("usuarios.id"))
    tutor_id = Column(String, ForeignKey("usuarios.id"))
    supervisor_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    
    estado = Column(String(20), default="activa") 
    horas_totales_requeridas = Column(Integer, default=320)
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    
    # Relaciones
    empresa = relationship("Empresa", back_populates="practicas")
    seguimientos = relationship("Seguimiento", back_populates="practica")
    estudiante = relationship("Usuario", foreign_keys=[estudiante_id])
    tutor = relationship("Usuario", foreign_keys=[tutor_id])

class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    practica_id = Column(String, ForeignKey("practicas.id"))
    fecha_actividad = Column(DateTime, default=datetime.datetime.utcnow)
    descripcion = Column(Text, nullable=False)
    horas_realizadas = Column(Float, nullable=False)
    
    # Combinación de estados y validaciones
    estado = Column(Enum(StatusEnum), default=StatusEnum.BORRADOR)
    validado_tutor = Column(Boolean, default=False)
    validado_supervisor = Column(Boolean, default=False)
    
    observaciones_tutor = Column(Text, nullable=True)
    evidencia_url = Column(String, nullable=True) # URL del archivo
    archivo_evidencia = Column(String, nullable=True) # Nombre/Path local
    is_deleted = Column(Boolean, default=False)
    
    practica = relationship("Practica", back_populates="seguimientos")

class AuditLog(Base):
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String)
    accion = Column(String) 
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    ip_origen = Column(String)
