from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import uuid
import enum

# --- ENUMS ---
class UserRole(str, enum.Enum):
    """Roles de usuario soportados por el sistema."""
    ESTUDIANTE = "estudiante"
    TUTOR = "tutor"
    SUPERVISOR = "supervisor"
    COORDINADOR = "coordinador"

class StatusEnum(str, enum.Enum):
    """Estados posibles para un seguimiento."""
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"

# --- MODELOS ---

class Usuario(Base):
    """Modelo para gestionar los usuarios del sistema."""
    __tablename__ = "usuarios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(UserRole), default=UserRole.ESTUDIANTE)
    programa_academico = Column(String, nullable=True) 
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones para facilitar consultas inversas
    seguimientos_validados = relationship("AuditLog", back_populates="usuario")

class Empresa(Base):
    """Modelo para las empresas donde se realizan las prácticas."""
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), unique=True, index=True, nullable=False)
    nit = Column(String(50), unique=True)
    direccion = Column(String(255))
    
    practicas = relationship("Practica", back_populates="empresa")

class Practica(Base):
    """Modelo que vincula a un estudiante con su tutor y supervisor en una empresa."""
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
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])

class Seguimiento(Base):
    """Modelo para el registro de actividades diarias/semanales del estudiante."""
    __tablename__ = "seguimientos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    practica_id = Column(String, ForeignKey("practicas.id"))
    fecha_actividad = Column(DateTime, default=datetime.datetime.utcnow)
    descripcion = Column(Text, nullable=False)
    horas_realizadas = Column(Float, nullable=False)
    
    estado = Column(Enum(StatusEnum), default=StatusEnum.BORRADOR)
    validado_tutor = Column(Boolean, default=False)
    validado_supervisor = Column(Boolean, default=False)
    
    observaciones_tutor = Column(Text, nullable=True)
    evidencia_url = Column(String, nullable=True) 
    archivo_evidencia = Column(String, nullable=True) 
    is_deleted = Column(Boolean, default=False)
    
    practica = relationship("Practica", back_populates="seguimientos")

class AuditLog(Base):
    """Registro de auditoría para acciones críticas."""
    __tablename__ = "logs_auditoria"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"))
    accion = Column(String) 
    fecha = Column(DateTime, default=datetime.datetime.utcnow)
    ip_origen = Column(String)

    usuario = relationship("Usuario", back_populates="seguimientos_validados")

