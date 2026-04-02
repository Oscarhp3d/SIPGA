from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Text, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20)) # 'estudiante', 'tutor', 'supervisor', 'coordinador'
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), unique=True, index=True)
    nit = Column(String(50), unique=True)
    direccion = Column(String(255))
    
    # Relación inversa (opcional pero recomendada)
    practicas = relationship("Practica", back_populates="empresa")

class Practica(Base):
    __tablename__ = "practicas"
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("usuarios.id"))
    tutor_id = Column(Integer, ForeignKey("usuarios.id"))
    supervisor_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # Cambio: Ahora apunta a la tabla empresas
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    estado = Column(String(20), default="activa") # 'activa', 'finalizada'
    
    # Relaciones
    estudiante = relationship("Usuario", foreign_keys=[estudiante_id])
    tutor = relationship("Usuario", foreign_keys=[tutor_id])
    empresa = relationship("Empresa", back_populates="practicas")

class Seguimiento(Base):
    __tablename__ = "seguimientos"
    id = Column(Integer, primary_key=True, index=True)
    practica_id = Column(Integer, ForeignKey("practicas.id"))
    fecha_actividad = Column(DateTime, default=datetime.datetime.utcnow)
    descripcion = Column(Text)
    horas_realizadas = Column(Float)
    validado_tutor = Column(Boolean, default=False)
    validado_supervisor = Column(Boolean, default=False)
    archivo_evidencia = Column(String, nullable=True)
    estado = Column(String, default="Pendiente") # 'Pendiente', 'Aprobado', 'Rechazado'
    observaciones_tutor = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
