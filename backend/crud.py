from sqlalchemy.orm import Session
import models, schemas
import auth

# --- LÓGICA DE AUDITORÍA (Misión Crítica) ---

def create_audit_log(db: Session, usuario_id: str, accion: str, ip: str):
    """Registra cualquier acción sensible en el sistema."""
    db_log = models.AuditLog(
        usuario_id=usuario_id,
        accion=accion,
        ip_origen=ip
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

# --- LÓGICA DE USUARIOS ---

def obtener_usuarios(db: Session):
    return db.query(models.Usuario).all()

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate):
    password_cifrada = auth.hash_password(usuario.password)
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        correo=usuario.correo,
        password_hash=password_cifrada, # Mantenido de bloque 1
        hashed_password=password_cifrada, # Mantenido de bloque 2
        rol=usuario.rol,
        programa_academico=usuario.programa_academico
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# --- LÓGICA DE PRÁCTICAS ---

def crear_practica(db: Session, estudiante_id: str, tutor_id: str, supervisor_id: str, empresa_id: int):
    db_practica = models.Practica(
        estudiante_id=estudiante_id,
        tutor_id=tutor_id,
        supervisor_id=supervisor_id,
        empresa_id=empresa_id
    )
    db.add(db_practica)
    db.commit()
    db.refresh(db_practica)
    return db_practica

# --- LÓGICA DE SEGUIMIENTO ---

def registrar_seguimiento(db: Session, seguimiento: schemas.SeguimientoCreate):
    db_seguimiento = models.Seguimiento(
        practica_id=seguimiento.practica_id,
        descripcion=seguimiento.descripcion,
        horas_realizadas=seguimiento.horas_realizadas,
        fecha_actividad=seguimiento.fecha_actividad
    )
    db.add(db_seguimiento)
    db.commit()
    db.refresh(db_seguimiento)
    return db_seguimiento

def obtener_seguimientos_practica(db: Session, practica_id: str):
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.practica_id == practica_id,
        models.Seguimiento.is_deleted == False
    ).all()

# --- VALIDACIÓN Y FASE DE REVISIÓN ---

def validar_seguimiento(db: Session, seguimiento_id: str, estado: models.StatusEnum, tutor_id: str, observaciones: str, ip: str):
    """Actualiza el estado y registra la acción en la auditoría."""
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.estado = estado
        db_seg.observaciones_tutor = observaciones
        # Sincronización con booleanos de validación antiguos
        if estado == models.StatusEnum.APROBADO:
            db_seg.validado_tutor = True
        elif estado == models.StatusEnum.RECHAZADO:
            db_seg.validado_tutor = False
            
        db.commit()
        create_audit_log(db, tutor_id, f"CAMBIO ESTADO A {estado} EN SEGUIMIENTO {seguimiento_id}", ip)
        return db_seg
    return None

def validar_seguimiento_tutor(db: Session, seguimiento_id: str):
    db_seguimiento = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seguimiento:
        db_seguimiento.validado_tutor = True
        db_seguimiento.estado = models.StatusEnum.APROBADO
        db.commit()
        db.refresh(db_seguimiento)
    return db_seguimiento

def validar_seguimiento_supervisor(db: Session, seguimiento_id: str):
    db_seguimiento = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seguimiento:
        db_seguimiento.validado_supervisor = True
        db.commit()
        db.refresh(db_seguimiento)
    return db_seguimiento

def rechazar_seguimiento(db: Session, seguimiento_id: str, observaciones: str):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.estado = models.StatusEnum.RECHAZADO
        db_seg.observaciones_tutor = observaciones
        db_seg.validado_tutor = False
        db.commit()
        db.refresh(db_seg)
    return db_seg

def actualizar_evidencia(db: Session, seguimiento_id: str, ruta_archivo: str):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.archivo_evidencia = ruta_archivo
        db_seg.evidencia_url = ruta_archivo # Actualizamos ambos campos de evidencia
        db.commit()
    return db_seg

def eliminar_seguimiento_logico(db: Session, seguimiento_id: str):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.is_deleted = True
        db.commit()
    return db_seg
