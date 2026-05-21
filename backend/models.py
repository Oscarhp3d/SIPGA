from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from database import Base
import datetime
import enum
import uuid


class UserRole(str, enum.Enum):
    estudiante  = "estudiante"
    tutor       = "tutor"
    supervisor  = "supervisor"
    coordinador = "coordinador"

class StatusEnum(str, enum.Enum):
    borrador             = "borrador"
    enviado              = "enviado"
    pendiente_tutor      = "pendiente_tutor"
    pendiente_supervisor = "pendiente_supervisor"
    aprobado             = "aprobado"
    rechazado            = "rechazado"
    validado_final       = "validado_final"

userrole_type   = Enum(UserRole,  name="userrole",   create_type=False)
statusenum_type = Enum(StatusEnum, name="statusenum", create_type=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id                 = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    nombre             = Column(String(100), nullable=False)
    correo             = Column(String(150), unique=True, nullable=False, index=True)
    password_hash      = Column(String(255), nullable=False)
    rol                = Column(userrole_type, default=UserRole.estudiante)
    programa_academico = Column(String, nullable=True)
    fecha_creacion     = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    acepto_politica      = Column(Boolean, nullable=False, default=False)
    fecha_consentimiento = Column(DateTime, nullable=True)
    version_politica     = Column(String(20), nullable=True)

    audit_logs = relationship(
        "AuditLog",
        back_populates="usuario"
    )


class Empresa(Base):
    __tablename__ = "empresas"

    id        = Column(Integer, primary_key=True, index=True)
    nombre    = Column(String(150), unique=True, index=True, nullable=False)
    nit       = Column(String(50), unique=True)
    direccion = Column(String(255))

    practicas = relationship("Practica", back_populates="empresa")


class AsignacionTutor(Base):
    __tablename__ = "asignaciones_tutor"

    id                 = Column(Integer, primary_key=True, index=True)
    tutor_id           = Column(String, ForeignKey("usuarios.id"), nullable=False)
    programa_academico = Column(String(200), nullable=False)
    fecha_asignacion   = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    activa             = Column(Boolean, default=True)

    tutor = relationship("Usuario", foreign_keys=[tutor_id])


class Practica(Base):
    __tablename__ = "practicas"

    id                       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    estudiante_id            = Column(String, ForeignKey("usuarios.id"))
    tutor_id                 = Column(String, ForeignKey("usuarios.id"), nullable=True)
    supervisor_id            = Column(String, ForeignKey("usuarios.id"), nullable=True)
    empresa_id               = Column(Integer, ForeignKey("empresas.id"))
    estado                   = Column(String(20), default="activa")
    horas_totales_requeridas = Column(Integer, default=320)
    horas_acumuladas         = Column(Float, default=0.0)
    fecha_inicio             = Column(DateTime)
    fecha_fin                = Column(DateTime)

    empresa      = relationship("Empresa", back_populates="practicas")
    seguimientos = relationship("Seguimiento", back_populates="practica")
    estudiante   = relationship("Usuario", foreign_keys=[estudiante_id])
    tutor        = relationship("Usuario", foreign_keys=[tutor_id])
    supervisor   = relationship("Usuario", foreign_keys=[supervisor_id])


class Seguimiento(Base):
    __tablename__ = "seguimientos"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    practica_id     = Column(Integer, ForeignKey("practicas.id"))
    fecha_actividad = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    descripcion     = Column(Text, nullable=False)
    horas_realizadas = Column(Float, nullable=False)
    estado          = Column(statusenum_type, default=StatusEnum.borrador)
    validado_tutor       = Column(Boolean, default=False)
    validado_supervisor  = Column(Boolean, default=False)
    observaciones_tutor  = Column(Text, nullable=True)
    evidencia_url        = Column(String, nullable=True)
    archivo_evidencia    = Column(String, nullable=True)
    is_deleted           = Column(Boolean, default=False)

    practica = relationship("Practica", back_populates="seguimientos")


class EmpresaSupervisor(Base):
    """Vincula un supervisor (usuario de la empresa) con una empresa específica."""
    __tablename__ = "empresa_supervisores"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    empresa_id       = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    supervisor_id    = Column(String, ForeignKey("usuarios.id"), nullable=False)
    activo           = Column(Boolean, default=True)
    fecha_asignacion = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    empresa    = relationship("Empresa")
    supervisor = relationship("Usuario", foreign_keys=[supervisor_id])


class AuditLog(Base):
    __tablename__ = "logs_auditoria"

    id         = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(String, ForeignKey("usuarios.id"), nullable=True)
    accion     = Column(String)
    fecha      = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    ip_origen  = Column(String)

    usuario = relationship("Usuario", back_populates="audit_logs")

class Notificacion(Base):
    __tablename__ = "notificaciones"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id     = Column(String, ForeignKey("usuarios.id"), nullable=False)
    titulo         = Column(String(200), nullable=False)
    mensaje        = Column(Text, nullable=False)
    leida          = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    usuario = relationship("Usuario")