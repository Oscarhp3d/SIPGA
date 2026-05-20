from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
import models, schemas
import auth
import uuid
from datetime import datetime, timezone


def create_audit_log(db: Session, usuario_id: str, accion: str, ip: str) -> models.AuditLog:
    db_log = models.AuditLog(usuario_id=usuario_id, accion=accion, ip_origen=ip)
    db.add(db_log)
    db.commit()
    return db_log


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
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        return False
    # Verificar si tiene prácticas asociadas
    practicas = db.query(models.Practica).filter(models.Practica.empresa_id == empresa_id).first()
    if practicas:
        raise ValueError("No se puede eliminar la empresa porque tiene prácticas asociadas.")
    
    db.delete(empresa)
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
    db_seg = models.Seguimiento(
        practica_id=seguimiento.practica_id,
        descripcion=seguimiento.descripcion,
        horas_realizadas=seguimiento.horas_realizadas,
        fecha_actividad=seguimiento.fecha_actividad,
        estado=models.StatusEnum.enviado
    )
    db.add(db_seg)
    db.commit()
    db.refresh(db_seg)
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
    FLUJO: supervisor aprueba primero → tutor valida después."""
    practicas_ids = [
        p.id for p in db.query(models.Practica).filter(
            models.Practica.tutor_id == tutor_id
        ).all()
    ]
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.practica_id.in_(practicas_ids),
        models.Seguimiento.estado == models.StatusEnum.pendiente_tutor,
        models.Seguimiento.is_deleted == False
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
    if observaciones:
        db_seg.observaciones_tutor = observaciones

    db.commit()
    db.refresh(db_seg)
    create_audit_log(
        db, supervisor_id,
        f"SUPERVISOR APROBÓ seguimiento={seguimiento_id} → pendiente tutor",
        ip
    )
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
    return db_seg

def validar_seguimiento(
    db: Session,
    seguimiento_id: int,
    estado_solicitado: models.StatusEnum,
    revisor_id: str,
    observaciones: str,
    ip: str
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
        elif estado_solicitado == models.StatusEnum.rechazado:
            nuevo_estado = models.StatusEnum.rechazado
            db_seg.validado_supervisor = False
            
    elif revisor.rol == models.UserRole.tutor:
        if estado_solicitado == models.StatusEnum.aprobado:
            nuevo_estado = models.StatusEnum.aprobado
            db_seg.validado_tutor = True
        elif estado_solicitado == models.StatusEnum.rechazado:
            nuevo_estado = models.StatusEnum.rechazado
            db_seg.validado_tutor = False
            
    elif revisor.rol == models.UserRole.coordinador:
        if estado_solicitado == models.StatusEnum.aprobado:
            db_seg.validado_supervisor = True
            db_seg.validado_tutor = True
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
    return db_seg

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
        db_seg.archivo_evidencia = ruta_archivo
        db_seg.evidencia_url = ruta_archivo
        db.commit()
        db.refresh(db_seg)
    return db_seg




def crear_empresa(db: Session, empresa: schemas.EmpresaCreate) -> models.Empresa:
    db_empresa = models.Empresa(
        nombre=empresa.nombre,
        nit=empresa.nit,
        direccion=empresa.direccion
    )
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def obtener_empresas(db: Session) -> List[models.Empresa]:
    return db.query(models.Empresa).all()


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

def dashboard_estudiante(db: Session, estudiante_id: str) -> dict:
    practicas = obtener_practicas_por_usuario(db, estudiante_id, "estudiante")
    practica = practicas[0] if practicas else None
    horas_acum = practica.horas_acumuladas if practica else 0.0
    horas_req = practica.horas_totales_requeridas if practica else 320
    porcentaje = round((horas_acum / horas_req) * 100, 1) if horas_req > 0 else 0.0

    seguimientos_recientes = []
    if practica:
        seguimientos_recientes = obtener_seguimientos_practica(db, practica.id)[-5:]

    return {
        "practica": practica,
        "horas_acumuladas": horas_acum,
        "horas_requeridas": horas_req,
        "porcentaje_avance": porcentaje,
        "seguimientos_recientes": seguimientos_recientes
    }