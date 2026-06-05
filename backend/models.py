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

    # Usuario conserva UUID (no cambia — es la clave de auth/JWT)
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
    fecha_inicio_convenio = Column(DateTime, nullable=True)
    fecha_fin_convenio    = Column(DateTime, nullable=True)
    cupos_totales         = Column(Integer, default=0, nullable=True)

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
    codigo_certificado       = Column(String(50), unique=True, nullable=True)

    empresa      = relationship("Empresa", back_populates="practicas")
    seguimientos = relationship("Seguimiento", back_populates="practica")
    estudiante   = relationship("Usuario", foreign_keys=[estudiante_id])
    tutor        = relationship("Usuario", foreign_keys=[tutor_id])
    supervisor   = relationship("Usuario", foreign_keys=[supervisor_id])
    evaluaciones = relationship("EvaluacionPractica", back_populates="practica", cascade="all, delete-orphan")

    @property
    def calificacion(self) -> float:
        import json
        
        # 1. Nota de seguimientos (bitácoras)
        calificaciones_informes = []
        if self.seguimientos:
            for s in self.seguimientos:
                estado_str = s.estado.value if hasattr(s.estado, "value") else s.estado
                if estado_str == "aprobado" and not s.is_deleted:
                    notas_informe = []
                    if s.calificacion_tutor is not None:
                        notas_informe.append(s.calificacion_tutor)
                    if s.calificacion_supervisor is not None:
                        notas_informe.append(s.calificacion_supervisor)
                    if notas_informe:
                        calificaciones_informes.append(sum(notas_informe) / len(notas_informe))
        
        nota_bitacoras = 0.0
        if calificaciones_informes:
            nota_bitacoras = sum(calificaciones_informes) / len(calificaciones_informes)
            
        # 2. Nota de evaluaciones de desempeño 360 (tutor/supervisor)
        notas_evaluaciones = []
        if hasattr(self, "evaluaciones") and self.evaluaciones:
            for ev in self.evaluaciones:
                try:
                    items = json.loads(ev.calificaciones_items)
                    if isinstance(items, dict) and items:
                        promedio_ev = sum(items.values()) / len(items)
                        notas_evaluaciones.append(promedio_ev)
                except Exception:
                    pass
                    
        nota_evaluaciones = 0.0
        if notas_evaluaciones:
            nota_evaluaciones = sum(notas_evaluaciones) / len(notas_evaluaciones)
            
        # 3. Ponderación final
        if calificaciones_informes and notas_evaluaciones:
            nota_final = 0.40 * nota_bitacoras + 0.60 * nota_evaluaciones
        elif calificaciones_informes:
            nota_final = nota_bitacoras
        elif notas_evaluaciones:
            nota_final = nota_evaluaciones
        else:
            nota_final = 0.0
            
        return round(nota_final, 2)

    @property
    def alerta_progreso(self) -> str:
        seguimientos_validos = [s for s in self.seguimientos if not s.is_deleted]
        hoy = datetime.datetime.now(datetime.timezone.utc)
        
        if seguimientos_validos:
            seguimientos_ordenados = sorted(seguimientos_validos, key=lambda x: x.fecha_actividad or datetime.datetime.min, reverse=True)
            ultimo_seg = seguimientos_ordenados[0]
            fecha_act = ultimo_seg.fecha_actividad
            if fecha_act:
                if fecha_act.tzinfo is None:
                    fecha_act = fecha_act.replace(tzinfo=datetime.timezone.utc)
                if (hoy - fecha_act).days > 7:
                    return "inactividad"
        elif self.fecha_inicio:
            fecha_ini = self.fecha_inicio
            if fecha_ini.tzinfo is None:
                fecha_ini = fecha_ini.replace(tzinfo=datetime.timezone.utc)
            if (hoy - fecha_ini).days > 7:
                return "inactividad"
                
        if self.fecha_inicio and self.fecha_fin:
            fecha_ini = self.fecha_inicio
            fecha_f = self.fecha_fin
            if fecha_ini.tzinfo is None:
                fecha_ini = fecha_ini.replace(tzinfo=datetime.timezone.utc)
            if fecha_f.tzinfo is None:
                fecha_f = fecha_f.replace(tzinfo=datetime.timezone.utc)
                
            dias_totales = (fecha_f - fecha_ini).days
            dias_transcurridos = (hoy - fecha_ini).days
            
            if dias_totales > 0 and dias_transcurridos > 0:
                horas_acum = self.horas_acumuladas or 0.0
                horas_req = self.horas_totales_requeridas or 320
                if horas_acum >= horas_req:
                    return "ok"
                tasa_actual = horas_acum / dias_transcurridos
                horas_proyectadas = tasa_actual * dias_totales
                if horas_proyectadas < horas_req:
                    return "retraso"
        return "ok"



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
    calificacion_tutor      = Column(Float, nullable=True)
    calificacion_supervisor = Column(Float, nullable=True)
    fecha_envio             = Column(DateTime, nullable=True)
    fecha_preaprobacion     = Column(DateTime, nullable=True)
    fecha_aprobacion        = Column(DateTime, nullable=True)


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


class HistorialSeguimiento(Base):
    __tablename__ = "historial_seguimientos"

    id                   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    seguimiento_id       = Column(Integer, ForeignKey("seguimientos.id"), nullable=False)
    descripcion_anterior = Column(Text, nullable=False)
    horas_anteriores     = Column(Float, nullable=False)
    fecha_modificacion   = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    usuario_id           = Column(String, ForeignKey("usuarios.id"), nullable=False)

    seguimiento = relationship("Seguimiento")
    usuario     = relationship("Usuario")


class EvaluacionPractica(Base):
    __tablename__ = "evaluaciones_practicas"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)
    practica_id         = Column(Integer, ForeignKey("practicas.id"), nullable=False)
    tipo                = Column(String(20), nullable=False)  # "parcial" o "final"
    evaluador_rol       = Column(String(20), nullable=False)  # "supervisor" o "tutor"
    calificaciones_items = Column(String, nullable=False)      # JSON string
    observaciones       = Column(Text, nullable=True)
    fecha               = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    practica = relationship("Practica", back_populates="evaluaciones")