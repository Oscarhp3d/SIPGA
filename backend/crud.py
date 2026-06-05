from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
import models, schemas
import auth
import uuid
import os
from datetime import datetime, timezone, timedelta


def create_audit_log(db: Session, usuario_id: str, accion: str, ip: str) -> models.AuditLog:
    db_log = models.AuditLog(usuario_id=usuario_id, accion=accion, ip_origen=ip)
    db.add(db_log)
    db.commit()
    return db_log


def crear_notificacion(db: Session, usuario_id: str, titulo: str, mensaje: str):
    if not usuario_id:
        return
    notif = models.Notificacion(usuario_id=usuario_id, titulo=titulo, mensaje=mensaje)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def obtener_usuarios(db: Session) -> List[models.Usuario]:
    return db.query(models.Usuario).all()

def obtener_usuario_por_id(db: Session, usuario_id: str) -> Optional[models.Usuario]:
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def obtener_usuario_por_correo(db: Session, correo: str) -> Optional[models.Usuario]:
    return db.query(models.Usuario).filter(models.Usuario.correo == correo).first()

def obtener_usuarios_por_rol(db: Session, rol: models.UserRole) -> List[models.Usuario]:
    return db.query(models.Usuario).filter(models.Usuario.rol == rol).all()

def obtener_tutores(db: Session) -> List[models.Usuario]:
    return obtener_usuarios_por_rol(db, models.UserRole.tutor)

def obtener_estudiantes(db: Session) -> List[models.Usuario]:
    return obtener_usuarios_por_rol(db, models.UserRole.estudiante)

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    """
    Crea un usuario desde el panel del coordinador.
    El consentimiento se registra automáticamente porque la institución
    actúa como responsable del tratamiento al vincular al actor.
    Si el rol es supervisor y se envía empresa_id, el vínculo empresa↔supervisor
    se crea automáticamente.
    """
    db_usuario = models.Usuario(
        id=str(uuid.uuid4()),
        nombre=usuario.nombre,
        correo=usuario.correo,
        password_hash=auth.hash_password(usuario.password),
        rol=usuario.rol,
        programa_academico=usuario.programa_academico,
        acepto_politica=True,
        fecha_consentimiento=datetime.now(timezone.utc),
        version_politica="v1.0",
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)

    # Si es supervisor y viene empresa_id, crear el vínculo automáticamente
    if usuario.rol == models.UserRole.supervisor and usuario.empresa_id:
        # Desactivar vínculo anterior si existe
        db.query(models.EmpresaSupervisor).filter(
            models.EmpresaSupervisor.supervisor_id == db_usuario.id,
            models.EmpresaSupervisor.activo == True
        ).update({"activo": False})
        vinculo = models.EmpresaSupervisor(
            empresa_id=usuario.empresa_id,
            supervisor_id=db_usuario.id,
            activo=True
        )
        db.add(vinculo)
        db.commit()

    return db_usuario


def registrar_usuario_publico(
    db: Session,
    datos: schemas.RegistroPublicoCreate,
) -> models.Usuario:
    """
    Registro iniciado por el propio usuario (endpoint público /auth/registro).
    Persiste la aceptación explícita de la política de datos con marca de
    tiempo, cumpliendo Art. 9 Ley 1581/2012 y Art. 4 Decreto 1377/2013.
    """
    db_usuario = models.Usuario(
        id=str(uuid.uuid4()),
        nombre=datos.nombre,
        correo=datos.correo,
        password_hash=auth.hash_password(datos.password),
        rol=models.UserRole.estudiante,       # rol por defecto al auto-registrarse
        programa_academico=datos.programa_academico,
        acepto_politica=True,                 # validado en el schema (ValueError si False)
        fecha_consentimiento=datetime.now(timezone.utc),
        version_politica=datos.version_politica,
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


def asignar_tutor_a_programa(
    db: Session, data: schemas.AsignacionTutorCreate
) -> models.AsignacionTutor:
    """
    El coordinador asigna un tutor a un programa académico.
    Si ya existe una asignación activa para ese programa, la desactiva primero.
    """
    # Desactivar asignación anterior para ese programa
    db.query(models.AsignacionTutor).filter(
        models.AsignacionTutor.programa_academico == data.programa_academico,
        models.AsignacionTutor.activa == True
    ).update({"activa": False})
    db.commit()

    nueva = models.AsignacionTutor(
        tutor_id=data.tutor_id,
        programa_academico=data.programa_academico,
        activa=True
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def obtener_asignaciones(db: Session) -> List[models.AsignacionTutor]:
    return db.query(models.AsignacionTutor).filter(
        models.AsignacionTutor.activa == True
    ).all()

def eliminar_empresa(db: Session, empresa_id: int) -> bool:
    """Elimina empresa, vínculos con supervisores y prácticas asociadas (con sus seguimientos)."""
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        return False

    db.query(models.EmpresaSupervisor).filter(
        models.EmpresaSupervisor.empresa_id == empresa_id
    ).delete(synchronize_session=False)

    practicas = db.query(models.Practica).filter(
        models.Practica.empresa_id == empresa_id
    ).all()
    for practica in practicas:
        eliminar_practica(db, practica.id)

    db.delete(empresa)
    db.commit()
    return True


def eliminar_usuario(db: Session, usuario_id: str) -> bool:
    """Elimina usuario y datos asociados; borra prácticas donde es estudiante."""
    db_user = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_user:
        return False

    practicas_estudiante = db.query(models.Practica).filter(
        models.Practica.estudiante_id == usuario_id
    ).all()
    for practica in practicas_estudiante:
        eliminar_practica(db, practica.id)

    db.query(models.Practica).filter(
        models.Practica.tutor_id == usuario_id
    ).update({models.Practica.tutor_id: None}, synchronize_session=False)
    db.query(models.Practica).filter(
        models.Practica.supervisor_id == usuario_id
    ).update({models.Practica.supervisor_id: None}, synchronize_session=False)

    db.query(models.AsignacionTutor).filter(
        models.AsignacionTutor.tutor_id == usuario_id
    ).delete(synchronize_session=False)
    db.query(models.EmpresaSupervisor).filter(
        models.EmpresaSupervisor.supervisor_id == usuario_id
    ).delete(synchronize_session=False)
    db.query(models.Notificacion).filter(
        models.Notificacion.usuario_id == usuario_id
    ).delete(synchronize_session=False)
    db.query(models.AuditLog).filter(
        models.AuditLog.usuario_id == usuario_id
    ).delete(synchronize_session=False)

    db.delete(db_user)
    db.commit()
    return True

def obtener_tutor_por_programa(
    db: Session, programa: str
) -> Optional[models.Usuario]:
    """Devuelve el tutor activo asignado a un programa académico."""
    asig = db.query(models.AsignacionTutor).filter(
        models.AsignacionTutor.programa_academico == programa,
        models.AsignacionTutor.activa == True
    ).first()
    if asig:
        return db.query(models.Usuario).filter(models.Usuario.id == asig.tutor_id).first()
    return None



def crear_practica(db: Session, data: schemas.PracticaCreate) -> models.Practica:
    """
    Crea una práctica.
    - Si no se especifica tutor_id, intenta asignar automáticamente el tutor del programa.
    - Si no se especifica supervisor_id, busca el supervisor vinculado a la empresa.
    """
    tutor_id = data.tutor_id

    # Auto-asignación de tutor por programa si no se especificó
    if not tutor_id:
        estudiante = obtener_usuario_por_id(db, data.estudiante_id)
        if estudiante and estudiante.programa_academico:
            tutor = obtener_tutor_por_programa(db, estudiante.programa_academico)
            if tutor:
                tutor_id = tutor.id

    # Auto-asignación de supervisor por empresa si no se especificó
    supervisor_id = data.supervisor_id
    if not supervisor_id and data.empresa_id:
        vinculo = db.query(models.EmpresaSupervisor).filter(
            models.EmpresaSupervisor.empresa_id == data.empresa_id,
            models.EmpresaSupervisor.activo == True
        ).first()
        if vinculo:
            supervisor_id = vinculo.supervisor_id

    # Validar vigencia de convenio de la empresa si existe
    if data.empresa_id:
        empresa = db.query(models.Empresa).filter(models.Empresa.id == data.empresa_id).first()
        if empresa and (empresa.fecha_inicio_convenio or empresa.fecha_fin_convenio):
            hoy = datetime.now()
            if empresa.fecha_inicio_convenio and hoy < empresa.fecha_inicio_convenio:
                raise ValueError("El convenio marco con la empresa aún no ha iniciado.")
            if empresa.fecha_fin_convenio and hoy > empresa.fecha_fin_convenio:
                raise ValueError("El convenio marco con la empresa ha expirado.")

    db_practica = models.Practica(
        estudiante_id=data.estudiante_id,
        tutor_id=tutor_id,
        supervisor_id=supervisor_id,
        empresa_id=data.empresa_id,
        horas_totales_requeridas=data.horas_totales_requeridas,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin
    )
    db.add(db_practica)
    db.commit()
    db.refresh(db_practica)
    return db_practica

def obtener_practica(db: Session, practica_id: int) -> Optional[models.Practica]:
    return db.query(models.Practica).filter(models.Practica.id == practica_id).first()


def usuario_puede_ver_practica(
    db: Session, usuario: models.Usuario, practica: models.Practica
) -> bool:
    """Estudiante, tutor, supervisor de la práctica, coordinador o supervisor de la empresa."""
    rol = usuario.rol.value if hasattr(usuario.rol, "value") else usuario.rol
    if rol == "coordinador":
        return True
    if usuario.id in {practica.estudiante_id, practica.tutor_id, practica.supervisor_id}:
        return True
    if rol == "supervisor" and practica.empresa_id:
        vinculo = db.query(models.EmpresaSupervisor).filter(
            models.EmpresaSupervisor.empresa_id == practica.empresa_id,
            models.EmpresaSupervisor.supervisor_id == usuario.id,
            models.EmpresaSupervisor.activo == True,
        ).first()
        return vinculo is not None
    return False


def seguimiento_tiene_evidencia(seg: models.Seguimiento) -> bool:
    return bool(seg.evidencia_url or seg.archivo_evidencia)


def obtener_ruta_evidencia_fisica(seg: models.Seguimiento) -> Optional[str]:
    ruta = seg.evidencia_url or seg.archivo_evidencia
    if not ruta:
        return None
    ruta = ruta.replace("\\", "/")
    if os.path.isabs(ruta):
        return ruta if os.path.isfile(ruta) else None
    base = os.path.dirname(os.path.abspath(__file__))
    candidatas = [
        os.path.join(base, ruta),
        os.path.join(base, "..", ruta),
    ]
    for candidata in candidatas:
        if os.path.isfile(candidata):
            return os.path.normpath(candidata)
    return None

def obtener_todas_practicas(db: Session) -> List[models.Practica]:
    return db.query(models.Practica).all()

def obtener_practicas_por_usuario(
    db: Session, usuario_id: str, rol: str
) -> List[models.Practica]:
    if rol == "estudiante":
        return db.query(models.Practica).filter(
            models.Practica.estudiante_id == usuario_id
        ).all()
    elif rol == "tutor":
        return db.query(models.Practica).filter(
            models.Practica.tutor_id == usuario_id
        ).all()
    elif rol == "supervisor":
        return db.query(models.Practica).filter(
            models.Practica.supervisor_id == usuario_id
        ).all()
    return []

def reasignar_tutor_practica(
    db: Session, practica_id: int, nuevo_tutor_id: str
) -> Optional[models.Practica]:
    """El coordinador reasigna el tutor de una práctica específica."""
    practica = obtener_practica(db, practica_id)
    if not practica:
        return None
    practica.tutor_id = nuevo_tutor_id
    db.commit()
    db.refresh(practica)
    return practica

def eliminar_practica(db: Session, practica_id: int) -> bool:
    practica = db.query(models.Practica).filter(models.Practica.id == practica_id).first()
    if not practica:
        return False
    
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    
    # Eliminar historiales asociados a los seguimientos de esta práctica (por si existen en la BD)
    try:
        db.execute(text("""
            DELETE FROM seguimientos_historial 
            WHERE seguimiento_id IN (SELECT id FROM seguimientos WHERE practica_id = :practica_id)
        """), {"practica_id": practica_id})
    except SQLAlchemyError:
        db.rollback() # Ignorar si la tabla no existe
        
    try:
        db.execute(text("""
            DELETE FROM historial_seguimientos 
            WHERE seguimiento_id IN (SELECT id FROM seguimientos WHERE practica_id = :practica_id)
        """), {"practica_id": practica_id})
    except SQLAlchemyError:
        db.rollback() # Ignorar si la tabla no existe

    # Eliminar seguimientos asociados
    db.query(models.Seguimiento).filter(models.Seguimiento.practica_id == practica_id).delete(synchronize_session=False)
    
    db.delete(practica)
    db.commit()
    return True


def registrar_seguimiento(
    db: Session, seguimiento: schemas.SeguimientoCreate
) -> models.Seguimiento:
    # 1. Validar límite diario (<= 8 horas)
    fecha_act = seguimiento.fecha_actividad
    if fecha_act.tzinfo is None:
        fecha_act = fecha_act.replace(tzinfo=timezone.utc)
    
    inicio_dia = datetime(fecha_act.year, fecha_act.month, fecha_act.day, 0, 0, 0, tzinfo=timezone.utc)
    fin_dia = datetime(fecha_act.year, fecha_act.month, fecha_act.day, 23, 59, 59, tzinfo=timezone.utc)
    
    horas_hoy = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
        models.Seguimiento.practica_id == seguimiento.practica_id,
        models.Seguimiento.is_deleted == False,
        models.Seguimiento.fecha_actividad >= inicio_dia.replace(tzinfo=None),
        models.Seguimiento.fecha_actividad <= fin_dia.replace(tzinfo=None)
    ).scalar() or 0.0
    
    if horas_hoy + seguimiento.horas_realizadas > 8.0:
        raise ValueError(f"Límite diario excedido. Ya tienes {horas_hoy:g}h reportadas para este día. El reporte diario no puede exceder 8h.")
        
    # 2. Validar límite semanal (<= 48 horas en los últimos 7 días)
    inicio_semana = fecha_act - timedelta(days=7)
    horas_semana = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
        models.Seguimiento.practica_id == seguimiento.practica_id,
        models.Seguimiento.is_deleted == False,
        models.Seguimiento.fecha_actividad >= inicio_semana.replace(tzinfo=None),
        models.Seguimiento.fecha_actividad <= fecha_act.replace(tzinfo=None)
    ).scalar() or 0.0
    
    if horas_semana + seguimiento.horas_realizadas > 48.0:
        raise ValueError(f"Límite semanal excedido. Tienes {horas_semana:g}h reportadas en los últimos 7 días. El total no puede exceder 48h semanales.")

    db_seg = models.Seguimiento(
        practica_id=seguimiento.practica_id,
        descripcion=seguimiento.descripcion,
        horas_realizadas=seguimiento.horas_realizadas,
        fecha_actividad=seguimiento.fecha_actividad,
        estado=models.StatusEnum.enviado,
        fecha_envio=datetime.now(timezone.utc)
    )
    db.add(db_seg)
    db.commit()
    db.refresh(db_seg)

    # Notificar al supervisor o tutor cuando se crea el seguimiento
    practica = obtener_practica(db, seguimiento.practica_id)
    if practica:
        if practica.supervisor_id:
            crear_notificacion(db, practica.supervisor_id, "Nuevo seguimiento", f"El estudiante ha reportado {seguimiento.horas_realizadas} horas para validación.")
        elif practica.tutor_id:
            crear_notificacion(db, practica.tutor_id, "Nuevo seguimiento", f"El estudiante ha reportado {seguimiento.horas_realizadas} horas para validación.")

    return db_seg

def obtener_seguimientos_practica(
    db: Session, practica_id: int
) -> List[models.Seguimiento]:
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.practica_id == practica_id,
        models.Seguimiento.is_deleted == False
    ).all()

def obtener_seguimiento(
    db: Session, seguimiento_id: int
) -> Optional[models.Seguimiento]:
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.id == seguimiento_id
    ).first()

def obtener_seguimientos_pendientes_tutor(
    db: Session, tutor_id: str
) -> List[models.Seguimiento]:
    """Seguimientos aprobados por el supervisor (pendiente_tutor) que el tutor debe revisar.
    O seguimientos 'enviados' de prácticas que no tienen supervisor asignado."""
    from sqlalchemy import or_, and_
    return db.query(models.Seguimiento).join(
        models.Practica, models.Seguimiento.practica_id == models.Practica.id
    ).filter(
        models.Practica.tutor_id == tutor_id,
        models.Seguimiento.is_deleted == False,
        or_(
            models.Seguimiento.estado == models.StatusEnum.pendiente_tutor,
            and_(
                models.Seguimiento.estado == models.StatusEnum.enviado,
                models.Practica.supervisor_id == None
            )
        )
    ).all()

def obtener_seguimientos_pendientes_supervisor(
    db: Session, supervisor_id: str
) -> List[models.Seguimiento]:
    """Seguimientos enviados por el estudiante que el supervisor debe revisar primero.
    FLUJO: supervisor es la primera línea de validación."""
    practicas_ids = [
        p.id for p in db.query(models.Practica).filter(
            models.Practica.supervisor_id == supervisor_id
        ).all()
    ]
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.practica_id.in_(practicas_ids),
        models.Seguimiento.estado == models.StatusEnum.enviado,
        models.Seguimiento.is_deleted == False
    ).all()

def supervisor_aprobar_seguimiento(
    db: Session,
    seguimiento_id: int,
    supervisor_id: str,
    observaciones: str,
    ip: str
) -> Optional[models.Seguimiento]:
    """El supervisor aprueba las horas → pasan a pendiente_tutor para revisión del tutor."""
    db_seg = db.query(models.Seguimiento).filter(
        models.Seguimiento.id == seguimiento_id
    ).first()
    if not db_seg:
        return None

    db_seg.estado = models.StatusEnum.pendiente_tutor
    db_seg.validado_supervisor = True
    db_seg.fecha_preaprobacion = datetime.now(timezone.utc)
    if observaciones:
        db_seg.observaciones_tutor = observaciones

    db.commit()
    db.refresh(db_seg)
    create_audit_log(
        db, supervisor_id,
        f"SUPERVISOR APROBÓ seguimiento={seguimiento_id} → pendiente tutor",
        ip
    )
    
    practica = obtener_practica(db, db_seg.practica_id)
    if practica and practica.tutor_id:
        crear_notificacion(db, practica.tutor_id, "Seguimiento pre-aprobado", "El supervisor ha aprobado un seguimiento y requiere tu validación.")
    if practica and practica.estudiante_id:
        crear_notificacion(db, practica.estudiante_id, "Seguimiento validado", "Tu seguimiento ha sido aprobado por el supervisor.")
        
    return db_seg

def supervisor_rechazar_seguimiento(
    db: Session,
    seguimiento_id: int,
    supervisor_id: str,
    observaciones: str,
    ip: str
) -> Optional[models.Seguimiento]:
    """El supervisor rechaza las horas → vuelven al estudiante con observaciones."""
    db_seg = db.query(models.Seguimiento).filter(
        models.Seguimiento.id == seguimiento_id
    ).first()
    if not db_seg:
        return None

    db_seg.estado = models.StatusEnum.rechazado
    db_seg.validado_supervisor = False
    db_seg.observaciones_tutor = observaciones

    db.commit()
    db.refresh(db_seg)
    create_audit_log(
        db, supervisor_id,
        f"SUPERVISOR RECHAZÓ seguimiento={seguimiento_id}: {observaciones[:80]}",
        ip
    )
    
    practica = obtener_practica(db, db_seg.practica_id)
    if practica and practica.estudiante_id:
        crear_notificacion(db, practica.estudiante_id, "Seguimiento rechazado", "Tu seguimiento ha sido rechazado por el supervisor.")
        
    return db_seg

def validar_seguimiento(
    db: Session,
    seguimiento_id: int,
    estado_solicitado: models.StatusEnum,
    revisor_id: str,
    observaciones: str,
    ip: str,
    calificacion_tutor: Optional[float] = None,
    calificacion_supervisor: Optional[float] = None
) -> Optional[models.Seguimiento]:
    db_seg = db.query(models.Seguimiento).filter(
        models.Seguimiento.id == seguimiento_id
    ).first()
    if not db_seg:
        return None

    estado_anterior = db_seg.estado
    revisor = obtener_usuario_por_id(db, revisor_id)
    if not revisor:
        return None

    nuevo_estado = estado_solicitado

    if revisor.rol == models.UserRole.supervisor:
        if estado_solicitado == models.StatusEnum.aprobado:
            nuevo_estado = models.StatusEnum.pendiente_tutor
            db_seg.validado_supervisor = True
            db_seg.fecha_preaprobacion = datetime.now(timezone.utc)
            if calificacion_supervisor is not None:
                db_seg.calificacion_supervisor = calificacion_supervisor
        elif estado_solicitado == models.StatusEnum.rechazado:
            nuevo_estado = models.StatusEnum.rechazado
            db_seg.validado_supervisor = False
            
    elif revisor.rol == models.UserRole.tutor:
        if estado_solicitado == models.StatusEnum.aprobado:
            nuevo_estado = models.StatusEnum.aprobado
            db_seg.validado_tutor = True
            db_seg.fecha_aprobacion = datetime.now(timezone.utc)
            if calificacion_tutor is not None:
                db_seg.calificacion_tutor = calificacion_tutor
        elif estado_solicitado == models.StatusEnum.rechazado:
            nuevo_estado = models.StatusEnum.rechazado
            db_seg.validado_tutor = False
            
    elif revisor.rol == models.UserRole.coordinador:
        if estado_solicitado == models.StatusEnum.aprobado:
            db_seg.validado_supervisor = True
            db_seg.validado_tutor = True
            db_seg.fecha_preaprobacion = db_seg.fecha_preaprobacion or datetime.now(timezone.utc)
            db_seg.fecha_aprobacion = datetime.now(timezone.utc)
            if calificacion_tutor is not None:
                db_seg.calificacion_tutor = calificacion_tutor
            if calificacion_supervisor is not None:
                db_seg.calificacion_supervisor = calificacion_supervisor
        nuevo_estado = estado_solicitado

    db_seg.estado = nuevo_estado
    db_seg.observaciones_tutor = observaciones

    # Sumar horas solo si acaba de pasar a estado aprobado de forma definitiva
    if nuevo_estado == models.StatusEnum.aprobado and estado_anterior != models.StatusEnum.aprobado:
        practica = obtener_practica(db, db_seg.practica_id)
        if practica:
            practica.horas_acumuladas = (practica.horas_acumuladas or 0) + db_seg.horas_realizadas
            if practica.horas_acumuladas >= practica.horas_totales_requeridas:
                practica.estado = "finalizada"

    db.commit()
    db.refresh(db_seg)
    create_audit_log(
        db, revisor_id,
        f"VALIDACIÓN [{nuevo_estado.value.upper()}] seguimiento={seguimiento_id}",
        ip
    )
    
    practica = obtener_practica(db, db_seg.practica_id)
    if practica and practica.estudiante_id:
        estado_texto = "aprobado" if nuevo_estado in [models.StatusEnum.aprobado, models.StatusEnum.pendiente_tutor] else "rechazado"
        crear_notificacion(db, practica.estudiante_id, f"Seguimiento {estado_texto}", f"Tu seguimiento ahora tiene estado: {estado_texto}.")
        
    return db_seg

def validar_seguimientos_lote(
    db: Session,
    seguimiento_ids: List[int],
    estado_solicitado: models.StatusEnum,
    revisor_id: str,
    observaciones: str,
    ip: str,
    calificacion: Optional[float] = None
) -> List[models.Seguimiento]:
    res = []
    revisor = obtener_usuario_por_id(db, revisor_id)
    if not revisor:
        return res
        
    calificacion_tutor = None
    calificacion_supervisor = None
    
    rol = revisor.rol.value if hasattr(revisor.rol, 'value') else revisor.rol
    if rol == "tutor":
        calificacion_tutor = calificacion
    elif rol == "supervisor":
        calificacion_supervisor = calificacion
    elif rol == "coordinador":
        calificacion_tutor = calificacion
        calificacion_supervisor = calificacion

    for s_id in seguimiento_ids:
        seg = validar_seguimiento(
            db, s_id, estado_solicitado, revisor_id, observaciones, ip,
            calificacion_tutor=calificacion_tutor,
            calificacion_supervisor=calificacion_supervisor
        )
        if seg:
            res.append(seg)
    return res

# ── EMPRESA–SUPERVISOR (vínculo empresa ↔ supervisor) ─────────────────────────

def asignar_supervisor_empresa(
    db: Session, data: "schemas.EmpresaSupervisorCreate"
) -> models.EmpresaSupervisor:
    """Vincula un supervisor con una empresa. Desactiva el vínculo anterior si existía."""
    db.query(models.EmpresaSupervisor).filter(
        models.EmpresaSupervisor.supervisor_id == data.supervisor_id,
        models.EmpresaSupervisor.activo == True
    ).update({"activo": False})

    nueva = models.EmpresaSupervisor(
        empresa_id=data.empresa_id,
        supervisor_id=data.supervisor_id,
        activo=True
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def obtener_supervisores_empresa(
    db: Session, empresa_id: int
) -> List[models.EmpresaSupervisor]:
    return db.query(models.EmpresaSupervisor).filter(
        models.EmpresaSupervisor.empresa_id == empresa_id,
        models.EmpresaSupervisor.activo == True
    ).all()

def obtener_empresa_del_supervisor(
    db: Session, supervisor_id: str
) -> Optional[models.EmpresaSupervisor]:
    return db.query(models.EmpresaSupervisor).filter(
        models.EmpresaSupervisor.supervisor_id == supervisor_id,
        models.EmpresaSupervisor.activo == True
    ).first()

def asignar_supervisor_a_practica(
    db: Session, practica_id: int, supervisor_id: str
) -> Optional[models.Practica]:
    """Asigna directamente un supervisor a una práctica específica."""
    practica = obtener_practica(db, practica_id)
    if not practica:
        return None
    practica.supervisor_id = supervisor_id
    db.commit()
    db.refresh(practica)
    return practica

def eliminar_seguimiento_logico(
    db: Session, seguimiento_id: int
) -> Optional[models.Seguimiento]:
    db_seg = obtener_seguimiento(db, seguimiento_id)
    if db_seg:
        db_seg.is_deleted = True
        db.commit()
        db.refresh(db_seg)
    return db_seg

def actualizar_evidencia(
    db: Session, seguimiento_id: int, ruta_archivo: str
) -> Optional[models.Seguimiento]:
    db_seg = obtener_seguimiento(db, seguimiento_id)
    if db_seg:
        ruta_norm = ruta_archivo.replace("\\", "/")
        db_seg.archivo_evidencia = ruta_norm
        db_seg.evidencia_url = ruta_norm
        db.commit()
        db.refresh(db_seg)
    return db_seg




def crear_empresa(db: Session, empresa: schemas.EmpresaCreate) -> models.Empresa:
    db_empresa = models.Empresa(
        nombre=empresa.nombre,
        nit=empresa.nit,
        direccion=empresa.direccion,
        fecha_inicio_convenio=empresa.fecha_inicio_convenio,
        fecha_fin_convenio=empresa.fecha_fin_convenio,
        cupos_totales=empresa.cupos_totales
    )
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def obtener_empresas(db: Session) -> List[models.Empresa]:
    empresas = db.query(models.Empresa).all()
    for emp in empresas:
        ocupados = db.query(models.Practica).filter(
            models.Practica.empresa_id == emp.id,
            models.Practica.estado == "activa"
        ).count()
        emp.cupos_ocupados = ocupados
    return empresas


def dashboard_coordinador(db: Session) -> dict:
    total_estudiantes = db.query(models.Usuario).filter(
        models.Usuario.rol == models.UserRole.estudiante
    ).count()
    total_tutores = db.query(models.Usuario).filter(
        models.Usuario.rol == models.UserRole.tutor
    ).count()
    total_activas = db.query(models.Practica).filter(
        models.Practica.estado == "activa"
    ).count()

    # Prácticas agrupadas por programa del estudiante
    practicas_por_programa: Dict[str, int] = {}
    practicas = db.query(models.Practica).all()
    for p in practicas:
        if p.estudiante and p.estudiante.programa_academico:
            prog = p.estudiante.programa_academico
            practicas_por_programa[prog] = practicas_por_programa.get(prog, 0) + 1

    seguimientos_pendientes = db.query(models.Seguimiento).filter(
        models.Seguimiento.estado == models.StatusEnum.enviado,
        models.Seguimiento.is_deleted == False
    ).count()

    return {
        "total_estudiantes": total_estudiantes,
        "total_tutores": total_tutores,
        "total_practicas_activas": total_activas,
        "practicas_por_programa": practicas_por_programa,
        "seguimientos_pendientes": seguimientos_pendientes
    }

def dashboard_tutor(db: Session, tutor_id: str) -> dict:
    practicas = obtener_practicas_por_usuario(db, tutor_id, "tutor")
    pendientes = len(obtener_seguimientos_pendientes_tutor(db, tutor_id))
    total_horas = sum(p.horas_acumuladas or 0 for p in practicas)
    return {
        "mis_estudiantes": practicas,
        "seguimientos_pendientes": pendientes,
        "total_horas_validadas": total_horas
    }

def dashboard_supervisor(db: Session, supervisor_id: str) -> dict:
    practicas = obtener_practicas_por_usuario(db, supervisor_id, "supervisor")
    pendientes = len(obtener_seguimientos_pendientes_supervisor(db, supervisor_id))
    total_horas = sum(p.horas_acumuladas or 0 for p in practicas)
    return {
        "mis_practicantes": practicas,
        "seguimientos_pendientes": pendientes,
        "total_horas_en_practicas": total_horas,
    }

def dashboard_estudiante(db: Session, estudiante_id: str) -> dict:
    from sqlalchemy import func
    from datetime import date

    practicas = obtener_practicas_por_usuario(db, estudiante_id, "estudiante")
    practica = practicas[0] if practicas else None
    horas_acum = practica.horas_acumuladas if practica else 0.0
    horas_req = practica.horas_totales_requeridas if practica else 320
    porcentaje = round((horas_acum / horas_req) * 100, 1) if horas_req > 0 else 0.0
    horas_hoy = 0.0

    seguimientos_recientes = []
    if practica:
        hoy = date.today()
        horas_hoy = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
            models.Seguimiento.practica_id == practica.id,
            models.Seguimiento.is_deleted == False,
            func.date(models.Seguimiento.fecha_actividad) == hoy,
        ).scalar() or 0.0
        seguimientos_recientes = (
            db.query(models.Seguimiento)
            .filter(
                models.Seguimiento.practica_id == practica.id,
                models.Seguimiento.is_deleted == False,
            )
            .order_by(models.Seguimiento.fecha_actividad.desc())
            .limit(5)
            .all()
        )

    return {
        "practica": practica,
        "horas_hoy": round(float(horas_hoy), 1),
        "horas_acumuladas": horas_acum,
        "horas_requeridas": horas_req,
        "porcentaje_avance": porcentaje,
        "seguimientos_recientes": seguimientos_recientes,
    }


def obtener_analitica_coordinador(db: Session) -> dict:
    """
    Genera métricas analíticas avanzadas para el coordinador.
    - Comparativa de programas académicos (horas totales y promedio).
    - Ranking/Podio de los 10 mejores estudiantes basados en horas acumuladas.
    - Desempeño y estadísticas de validación de los tutores asignados.
    """
    from collections import defaultdict

    # 1. Comparativa de Programas
    practicas = db.query(models.Practica).all()
    programa_data = defaultdict(lambda: {
        "total_estudiantes": 0,
        "total_horas_acumuladas": 0.0,
        "total_porcentaje": 0.0,
        "completados": 0
    })
    
    for p in practicas:
        if p.estudiante and p.estudiante.programa_academico:
            prog = p.estudiante.programa_academico
            programa_data[prog]["total_estudiantes"] += 1
            programa_data[prog]["total_horas_acumuladas"] += (p.horas_acumuladas or 0.0)
            
            horas_req = p.horas_totales_requeridas or 320
            horas_acum = p.horas_acumuladas or 0.0
            porcentaje = round((horas_acum / horas_req) * 100, 1) if horas_req > 0 else 0.0
            programa_data[prog]["total_porcentaje"] += porcentaje
            if porcentaje >= 100.0:
                programa_data[prog]["completados"] += 1
            
    comparativa_programas = []
    for prog, data in programa_data.items():
        total_est = data["total_estudiantes"]
        total_h = data["total_horas_acumuladas"]
        promedio = round(total_h / total_est, 1) if total_est > 0 else 0.0
        promedio_progreso = round(data["total_porcentaje"] / total_est, 1) if total_est > 0 else 0.0
        comparativa_programas.append({
            "programa": prog,
            "total_estudiantes": total_est,
            "total_horas_acumuladas": total_h,
            "promedio_horas": promedio,
            "promedio_porcentaje_avance": promedio_progreso,
            "estudiantes_completados": data["completados"]
        })
    comparativa_programas.sort(key=lambda x: x["total_horas_acumuladas"], reverse=True)

    # 2. Podio para los mejores practicantes
    practicas_ordenadas = sorted(
        practicas, 
        key=lambda x: (x.calificacion or 0.0, x.horas_acumuladas or 0.0), 
        reverse=True
    )
    
    podio_practicantes = []
    posicion = 1
    for p in practicas_ordenadas:
        if p.estudiante:
            horas_req = p.horas_totales_requeridas or 320
            horas_acum = p.horas_acumuladas or 0.0
            porcentaje = round((horas_acum / horas_req) * 100, 1) if horas_req > 0 else 0.0
            
            calif = p.calificacion

            # Contar total de logs y rechazados
            logs_est = db.query(models.Seguimiento).filter(
                models.Seguimiento.practica_id == p.id,
                models.Seguimiento.is_deleted == False
            ).all()
            tot_logs = len(logs_est)
            rechazados = sum(1 for l in logs_est if l.estado == models.StatusEnum.rechazado)
            tasa_rech = round((rechazados / tot_logs) * 100, 1) if tot_logs > 0 else 0.0

            podio_practicantes.append({
                "posicion": posicion,
                "estudiante_id": p.estudiante_id,
                "practica_id": p.id,
                "nombre": p.estudiante.nombre,
                "programa": p.estudiante.programa_academico or "No asignado",
                "horas_acumuladas": horas_acum,
                "porcentaje_avance": porcentaje,
                "calificacion": calif,
                "tasa_rechazo": tasa_rech,
                "seguimientos_totales": tot_logs
            })
            posicion += 1
            if posicion > 10:
                break

    # 3. Desempeño de los Tutores
    tutores = obtener_tutores(db)
    desempeno_tutores = []
    
    for t in tutores:
        estudiantes_asig = db.query(models.Practica).filter(models.Practica.tutor_id == t.id).count()
        
        seguimientos_validados = db.query(models.Seguimiento).join(
            models.Practica, models.Seguimiento.practica_id == models.Practica.id
        ).filter(
            models.Practica.tutor_id == t.id,
            models.Seguimiento.validado_tutor == True,
            models.Seguimiento.is_deleted == False
        ).count()

        seguimientos_rechazados = db.query(models.Seguimiento).join(
            models.Practica, models.Seguimiento.practica_id == models.Practica.id
        ).filter(
            models.Practica.tutor_id == t.id,
            models.Seguimiento.estado == models.StatusEnum.rechazado,
            models.Seguimiento.is_deleted == False
        ).count()
        
        horas_validadas = db.query(func.sum(models.Seguimiento.horas_realizadas)).join(
            models.Practica, models.Seguimiento.practica_id == models.Practica.id
        ).filter(
            models.Practica.tutor_id == t.id,
            models.Seguimiento.validado_tutor == True,
            models.Seguimiento.is_deleted == False
        ).scalar() or 0.0
        
        promedio_val = round(horas_validadas / estudiantes_asig, 1) if estudiantes_asig > 0 else 0.0
        
        desempeno_tutores.append({
            "tutor_id": t.id,
            "nombre": t.nombre,
            "estudiantes_asignados": estudiantes_asig,
            "seguimientos_validados": seguimientos_validados,
            "horas_promedio_validadas": promedio_val,
            "seguimientos_rechazados": seguimientos_rechazados
        })
    desempeno_tutores.sort(key=lambda x: x["seguimientos_validados"], reverse=True)

    # 4. Tiempos de Ciclo de Aprobación
    segs_aprobados = db.query(models.Seguimiento).filter(
        models.Seguimiento.estado == models.StatusEnum.aprobado,
        models.Seguimiento.is_deleted == False
    ).all()
    
    tiempos_preaprobacion = []
    tiempos_aprobacion_final = []
    
    for s in segs_aprobados:
        if s.fecha_envio and s.fecha_preaprobacion:
            diff = (s.fecha_preaprobacion - s.fecha_envio).total_seconds() / 3600.0
            tiempos_preaprobacion.append(diff)
        if s.fecha_preaprobacion and s.fecha_aprobacion:
            diff = (s.fecha_aprobacion - s.fecha_preaprobacion).total_seconds() / 3600.0
            tiempos_aprobacion_final.append(diff)
            
    avg_pre = round(sum(tiempos_preaprobacion) / len(tiempos_preaprobacion), 1) if tiempos_preaprobacion else 0.0
    avg_aprob = round(sum(tiempos_aprobacion_final) / len(tiempos_aprobacion_final), 1) if tiempos_aprobacion_final else 0.0

    return {
        "comparativa_programas": comparativa_programas,
        "podio_practicantes": podio_practicantes,
        "desempeno_tutores": desempeno_tutores,
        "promedio_horas_preaprobacion": avg_pre,
        "promedio_horas_aprobacion": avg_aprob
    }


def editar_seguimiento(
    db: Session,
    seguimiento_id: int,
    nueva_descripcion: str,
    nuevas_horas: float,
    usuario_id: str
) -> models.Seguimiento:
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if not db_seg:
        return None

    fecha_act = db_seg.fecha_actividad
    if fecha_act.tzinfo is None:
        fecha_act = fecha_act.replace(tzinfo=timezone.utc)
    
    inicio_dia = datetime(fecha_act.year, fecha_act.month, fecha_act.day, 0, 0, 0, tzinfo=timezone.utc)
    fin_dia = datetime(fecha_act.year, fecha_act.month, fecha_act.day, 23, 59, 59, tzinfo=timezone.utc)
    
    horas_hoy = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
        models.Seguimiento.practica_id == db_seg.practica_id,
        models.Seguimiento.is_deleted == False,
        models.Seguimiento.id != seguimiento_id,
        models.Seguimiento.fecha_actividad >= inicio_dia.replace(tzinfo=None),
        models.Seguimiento.fecha_actividad <= fin_dia.replace(tzinfo=None)
    ).scalar() or 0.0
    
    if horas_hoy + nuevas_horas > 8.0:
        raise ValueError(f"Límite diario excedido. Ya tienes {horas_hoy:g}h reportadas para este día. El total no puede exceder 8h.")
    
    inicio_semana = fecha_act - timedelta(days=7)
    horas_semana = db.query(func.sum(models.Seguimiento.horas_realizadas)).filter(
        models.Seguimiento.practica_id == db_seg.practica_id,
        models.Seguimiento.is_deleted == False,
        models.Seguimiento.id != seguimiento_id,
        models.Seguimiento.fecha_actividad >= inicio_semana.replace(tzinfo=None),
        models.Seguimiento.fecha_actividad <= fecha_act.replace(tzinfo=None)
    ).scalar() or 0.0
    
    if horas_semana + nuevas_horas > 48.0:
        raise ValueError(f"Límite semanal excedido. Tienes {horas_semana:g}h reportadas en los últimos 7 días. El total no puede exceder 48h semanales.")

    if db_seg.estado == models.StatusEnum.rechazado:
        historial = models.HistorialSeguimiento(
            seguimiento_id=db_seg.id,
            descripcion_anterior=db_seg.descripcion,
            horas_anteriores=db_seg.horas_realizadas,
            usuario_id=usuario_id
        )
        db.add(historial)

    db_seg.descripcion = nueva_descripcion
    db_seg.horas_realizadas = nuevas_horas
    db_seg.estado = models.StatusEnum.enviado
    db_seg.fecha_envio = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(db_seg)
    return db_seg


def registrar_evaluacion_practica(
    db: Session, eval_data: schemas.EvaluacionPracticaCreate
) -> models.EvaluacionPractica:
    db_eval = models.EvaluacionPractica(
        practica_id=eval_data.practica_id,
        tipo=eval_data.tipo,
        evaluador_rol=eval_data.evaluador_rol,
        calificaciones_items=eval_data.calificaciones_items,
        observaciones=eval_data.observaciones
    )
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    return db_eval


def obtener_evaluaciones_practica(
    db: Session, practica_id: int
) -> List[models.EvaluacionPractica]:
    return db.query(models.EvaluacionPractica).filter(
        models.EvaluacionPractica.practica_id == practica_id
    ).all()


def obtener_alertas_criticas(db: Session) -> dict:
    hoy = datetime.now()
    
    # 1 y 2. Retrasos e Inactividades
    retrasos = []
    inactividades = []
    
    practicas = db.query(models.Practica).filter(models.Practica.estado == "activa").all()
    for p in practicas:
        alerta = p.alerta_progreso
        nombre_est = p.estudiante.nombre if p.estudiante else f"Estudiante #{p.estudiante_id}"
        programa = p.estudiante.programa_academico or "N/A"
        
        if alerta == "retraso":
            retrasos.append({
                "id": p.id,
                "estudiante": nombre_est,
                "programa": programa,
                "horas_acumuladas": p.horas_acumuladas or 0.0,
                "horas_requeridas": p.horas_totales_requeridas,
                "fecha_fin": p.fecha_fin.strftime("%Y-%m-%d") if p.fecha_fin else "N/A"
            })
        elif alerta == "inactividad":
            # Calcular última fecha
            ultima_fecha = "N/A"
            if p.seguimientos:
                segs = sorted([s for s in p.seguimientos if not s.is_deleted], key=lambda x: x.fecha_actividad or datetime.min, reverse=True)
                if segs and segs[0].fecha_actividad:
                    ultima_fecha = segs[0].fecha_actividad.strftime("%Y-%m-%d")
            elif p.fecha_inicio:
                ultima_fecha = p.fecha_inicio.strftime("%Y-%m-%d")
                
            inactividades.append({
                "id": p.id,
                "estudiante": nombre_est,
                "programa": programa,
                "ultima_actividad": ultima_fecha
            })
            
    # 3. Convenios por vencer
    convenios_vencer = []
    empresas = db.query(models.Empresa).all()
    for emp in empresas:
        if emp.fecha_fin_convenio:
            # Quitamos tz para restar con datetime.now() local
            fecha_fin = emp.fecha_fin_convenio.replace(tzinfo=None)
            dias_restantes = (fecha_fin - hoy).days
            if 0 <= dias_restantes <= 60:
                convenios_vencer.append({
                    "id": emp.id,
                    "empresa": emp.nombre,
                    "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                    "dias_restantes": dias_restantes,
                    "vencido": False
                })
            elif dias_restantes < 0:
                convenios_vencer.append({
                    "id": emp.id,
                    "empresa": emp.nombre,
                    "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
                    "dias_restantes": abs(dias_restantes),
                    "vencido": True
                })
                
    # 4. Cuellos de botella
    cuellos_botella = []
    limite = hoy - timedelta(days=5)
    segs_pendientes = db.query(models.Seguimiento).filter(
        models.Seguimiento.estado.in_([models.StatusEnum.enviado, models.StatusEnum.pendiente_tutor]),
        models.Seguimiento.is_deleted == False
    ).all()
    
    for s in segs_pendientes:
        f_envio = s.fecha_envio
        if f_envio:
            f_envio_naive = f_envio.replace(tzinfo=None)
            if f_envio_naive <= limite:
                nombre_est = s.practica.estudiante.nombre if s.practica and s.practica.estudiante else "Estudiante"
                pendiente_de = "Tutor" if s.estado == models.StatusEnum.pendiente_tutor else "Supervisor"
                dias_retraso = (hoy - f_envio_naive).days
                cuellos_botella.append({
                    "seguimiento_id": s.id,
                    "estudiante": nombre_est,
                    "horas": s.horas_realizadas,
                    "pendiente_de": pendiente_de,
                    "fecha_envio": f_envio_naive.strftime("%Y-%m-%d"),
                    "dias_retraso": dias_retraso
                })
                
    return {
        "retrasos": retrasos,
        "inactividades": inactividades,
        "convenios_vencer": convenios_vencer,
        "cuellos_botella": cuellos_botella
    }
