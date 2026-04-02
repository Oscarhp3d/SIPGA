from sqlalchemy.orm import Session
import models, schemas
import auth
# --- LÓGICA DE USUARIOS ---

def obtener_usuarios(db: Session):
    """Obtiene la lista de todos los usuarios registrados."""
    return db.query(models.Usuario).all()

def crear_usuario(db: Session, usuario: schemas.UsuarioCreate):
    """Crea un nuevo usuario (Estudiante, Tutor, Supervisor o Coordinador)."""
    # Nota: Aquí se implementará el hashing de password para cumplir con la Ley 1581
    password_cifrada = auth.hash_password(usuario.password)
    db_usuario = models.Usuario(
        nombre=usuario.nombre,
        correo=usuario.correo,
        password_hash=password_cifrada, 
        rol=usuario.rol
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario


# --- LÓGICA DE PRÁCTICAS ---

def crear_practica(db: Session, estudiante_id: int, tutor_id: int, supervisor_id: int, empresa: str):
    """Registra una nueva relación de práctica entre los tres actores."""
    db_practica = models.Practica(
        estudiante_id=estudiante_id,
        tutor_id=tutor_id,
        supervisor_id=supervisor_id,
        empresa_nombre=empresa
    )
    db.add(db_practica)
    db.commit()
    db.refresh(db_practica)
    return db_practica


# --- LÓGICA DE SEGUIMIENTO (CONTROL DE HORAS) ---

def registrar_seguimiento(db: Session, seguimiento: schemas.SeguimientoCreate):
    """Registra una nueva actividad o bitácora de horas para una práctica."""
    db_seguimiento = models.Seguimiento(
        practica_id=seguimiento.practica_id,
        descripcion=seguimiento.descripcion,
        horas_realizadas=seguimiento.horas_realizadas
    )
    db.add(db_seguimiento)
    db.commit()
    db.refresh(db_seguimiento)
    return db_seguimiento

def obtener_seguimientos_practica(db: Session, practica_id: int):
    """Obtiene todas las horas registradas de una práctica específica."""
    return db.query(models.Seguimiento).filter(models.Seguimiento.practica_id == practica_id).all()

# --- Lógica de Validación de Informes (Fase 3) ---

def validar_seguimiento_tutor(db: Session, seguimiento_id: int):
    db_seguimiento = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seguimiento:
        db_seguimiento.validado_tutor = True
        db.commit()
        db.refresh(db_seguimiento)
    return db_seguimiento

def validar_seguimiento_supervisor(db: Session, seguimiento_id: int):
    db_seguimiento = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seguimiento:
        db_seguimiento.validado_supervisor = True
        db.commit()
        db.refresh(db_seguimiento)
    return db_seguimiento

# Función para que el tutor rechace con comentarios
def rechazar_seguimiento(db: Session, seguimiento_id: int, observaciones: str):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.estado = "Rechazado"
        db_seg.observaciones_tutor = observaciones
        db_seg.validado_tutor = False # Se asegura de quitar la validación
        db.commit()
        db.refresh(db_seg)
    return db_seg

# Función para guardar la ruta del archivo
def actualizar_evidencia(db: Session, seguimiento_id: int, ruta_archivo: str):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.archivo_evidencia = ruta_archivo
        db.commit()
    return db_seg

def eliminar_seguimiento_logico(db: Session, seguimiento_id: int):
    db_seg = db.query(models.Seguimiento).filter(models.Seguimiento.id == seguimiento_id).first()
    if db_seg:
        db_seg.is_deleted = True # No lo borramos de la DB, solo lo marcamos
        db.commit()
    return db_seg