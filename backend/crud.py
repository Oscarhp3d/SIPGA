from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas
import auth
from datetime import datetime

# --- LÓGICA DE AUDITORÍA ---

def create_audit_log(db: Session, usuario_id: str, accion: str, ip: str) -> models.AuditLog:
    """Registra una acción en el log de auditoría."""
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

def obtener_usuarios(db: Session) -> List[models.Usuario]:
    """Obtiene todos los usuarios registrados."""
    return db.query(models.Usuario).all()

def obtener_usuario_por_correo(db: Session, correo: str) -> Optional[models.Usuario]:
    """Busca un usuario por su correo electrónico."""
    return db.query(models.Usuario).filter(models.Usuario.correo == correo).first()

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate) -> models.Usuario:
    """Crea un nuevo usuario con la contraseña hasheada."""
    password_cifrada = auth.hash_password(usuario.password)
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        correo=usuario.correo,
        password_hash=password_cifrada,
        rol=usuario.rol,
        programa_academico=usuario.programa_academico
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# --- LÓGICA DE PRÁCTICAS ---

def crear_practica(db: Session, data: schemas.PracticaCreate) -> models.Practica:
    """Crea un nuevo registro de práctica profesional."""
    db_practica = models.Practica(
        estudiante_id=data.estudiante_id,
        tutor_id=data.tutor_id,
        supervisor_id=data.supervisor_id,
        empresa_id=data.empresa_id,
        horas_totales_requeridas=data.horas_totales_requeridas,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin
    )
    db.add(db_practica)
    db.commit()
    db.refresh(db_practica)
    return db_practica

def obtener_practica(db: Session, practica_id: str) -> Optional[models.Practica]:
    """Obtiene una práctica por su ID."""
    return db.query(models.Practica).filter(models.Practica.id == practica_id).first()

# --- LÓGICA DE SEGUIMIENTO ---

def registrar_seguimiento(db: Session, seguimiento: schemas.SeguimientoCreate) -> models.Seguimiento:
    """Registra una nueva actividad de seguimiento."""
    db_seguimiento = models.Seguimiento(
        practica_id=seguimiento.practica_id,
        descripcion=seguimiento.descripcion,
        horas_realizadas=seguimiento.horas_realizadas,
        fecha_actividad=seguimiento.fecha_actividad,
        estado=models.StatusEnum.enviado  # ✅ CORREGIDO: era StatusEnum.ENVIADO
    )
    db.add(db_seguimiento)
    db.commit()
    db.refresh(db_seguimiento)
    return db_seguimiento

def obtener_seguimientos_practica(db: Session, practica_id: str) -> List[models.Seguimiento]:
    """Obtiene los seguimientos no eliminados de una práctica."""
    return db.query(models.Seguimiento).filter(
        models.Seguimiento.practica_id == practica_id,
        models.Seguimiento.is_deleted == False
    ).all()

def obtener_seguimiento(db: Session, seguimiento_id: str) -> Optional[models.Seguimiento]:
    """Obtiene un seguimiento específico por ID."""
    return db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()

# --- VALIDACIÓN Y FASE DE REVISIÓN ---

def validar_seguimiento(
    db: Session, 
    seguimiento_id: str, 
    estado: models.StatusEnum, 
    revisor_id: str, 
    observaciones: str, 
    ip: str
) -> Optional[models.Seguimiento]:
    """Actualiza el estado de un seguimiento y registra la auditoría."""
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if not db_seg:
        return None
        
    db_seg.estado = estado
    db_seg.observaciones_tutor = observaciones
    
    # Sincronización de validaciones según el rol del revisor
    revisor = db.query(models.Usuario).filter(models.Usuario.id == revisor_id).first()
    if revisor:
        # ✅ CORREGIDO: era UserRole.TUTOR / .SUPERVISOR / .COORDINADOR (mayúsculas)
        if revisor.rol == models.UserRole.tutor:
            db_seg.validado_tutor = (estado == models.StatusEnum.aprobado)
        elif revisor.rol == models.UserRole.supervisor:
            db_seg.validado_supervisor = (estado == models.StatusEnum.aprobado)
        elif revisor.rol == models.UserRole.coordinador:
            db_seg.validado_tutor = (estado == models.StatusEnum.aprobado)
            db_seg.validado_supervisor = (estado == models.StatusEnum.aprobado)

    db.commit()
    db.refresh(db_seg)
    create_audit_log(db, revisor_id, f"VALIDACIÓN: {estado} - SEGUIMIENTO: {seguimiento_id}", ip)
    return db_seg

def actualizar_evidencia(db: Session, seguimiento_id: str, ruta_archivo: str) -> Optional[models.Seguimiento]:
    """Asocia un archivo de evidencia a un seguimiento."""
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.archivo_evidencia = ruta_archivo
        db_seg.evidencia_url = ruta_archivo
        db.commit()
        db.refresh(db_seg)
    return db_seg

def eliminar_seguimiento_logico(db: Session, seguimiento_id: str) -> Optional[models.Seguimiento]:
    """Realiza un borrado lógico de un seguimiento."""
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.is_deleted = True
        db.commit()
        db.refresh(db_seg)
    return db_seg

# --- LÓGICA DE EMPRESAS ---

def crear_empresa(db: Session, empresa: schemas.EmpresaCreate) -> models.Empresa:
    """Registra una nueva empresa en el sistema."""
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
    """Lista todas las empresas."""
    return db.query(models.Empresa).all()