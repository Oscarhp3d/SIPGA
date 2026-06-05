"""
Router exclusivo del Coordinador.
Agrupa todas las acciones de gestión que solo el coordinador puede hacer.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File
import csv
import io
from sqlalchemy.orm import Session
from typing import List
import models, schemas, crud
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auth
from database import get_db

router = APIRouter(prefix="/coordinador", tags=["Coordinador"])

solo_coordinador = auth.verificar_rol(["coordinador"])


# ── DASHBOARD ────────────────────────────────────────────────
@router.get("/dashboard", response_model=schemas.DashboardCoordinador)
def dashboard(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Resumen general del sistema: estudiantes, tutores, prácticas y pendientes."""
    return crud.dashboard_coordinador(db)


# ── GESTIÓN DE USUARIOS ──────────────────────────────────────
@router.get("/tutores", response_model=List[schemas.UsuarioResponse])
def listar_tutores(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todos los tutores registrados."""
    return crud.obtener_tutores(db)

@router.get("/estudiantes", response_model=List[schemas.UsuarioResponse])
def listar_estudiantes(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todos los estudiantes registrados."""
    return crud.obtener_estudiantes(db)


# ── ASIGNACIÓN TUTOR → PROGRAMA ACADÉMICO ────────────────────
@router.post("/asignar-tutor", response_model=schemas.AsignacionTutorResponse, status_code=201)
def asignar_tutor_a_programa(
    data: schemas.AsignacionTutorCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(solo_coordinador)
):
    """
    Asigna un tutor a un programa académico completo.
    Todos los estudiantes de ese programa serán atendidos por este tutor.
    Si ya había un tutor asignado al programa, queda inactivo.
    """
    # Validar que el usuario asignado existe y es tutor
    tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    if tutor.rol != models.UserRole.tutor:
        raise HTTPException(status_code=400, detail="El usuario no tiene el rol de tutor")

    asignacion = crud.asignar_tutor_a_programa(db, data)
    crud.create_audit_log(
        db, admin.id,
        f"ASIGNACIÓN: tutor={tutor.nombre} → programa={data.programa_academico}",
        request.client.host
    )
    return asignacion

@router.get("/asignaciones", response_model=List[schemas.AsignacionTutorResponse])
def listar_asignaciones(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Lista todas las asignaciones activas de tutor por programa."""
    return crud.obtener_asignaciones(db)


# ── REASIGNAR TUTOR EN UNA PRÁCTICA ESPECÍFICA ───────────────
@router.patch("/practicas/{practica_id}/reasignar-tutor", response_model=schemas.PracticaResponse)
def reasignar_tutor(
    practica_id: int,
    data: schemas.PracticaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(solo_coordinador)
):
    """
    Cambia el tutor asignado a una práctica individual.
    Útil cuando hay excepciones a la asignación por programa.
    """
    if not data.tutor_id:
        raise HTTPException(status_code=400, detail="Debe enviar el nuevo tutor_id")
    tutor = crud.obtener_usuario_por_id(db, data.tutor_id)
    if not tutor or tutor.rol != models.UserRole.tutor:
        raise HTTPException(status_code=400, detail="tutor_id inválido o usuario no es tutor")

    practica = crud.reasignar_tutor_practica(db, practica_id, data.tutor_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")

    crud.create_audit_log(
        db, admin.id,
        f"REASIGNACIÓN: práctica={practica_id} → nuevo tutor={tutor.nombre}",
        request.client.host
    )
    return practica


# ── VER SEGUIMIENTOS DE CUALQUIER PRÁCTICA ───────────────────
@router.get("/practicas/{practica_id}/seguimientos", response_model=List[schemas.SeguimientoResponse])
def ver_seguimientos_practica(
    practica_id: int,
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """El coordinador puede ver todos los seguimientos de cualquier práctica."""
    practica = crud.obtener_practica(db, practica_id)
    if not practica:
        raise HTTPException(status_code=404, detail="Práctica no encontrada")
    return crud.obtener_seguimientos_practica(db, practica_id)


# ── ANALÍTICAS AVANZADAS ─────────────────────────────────────
@router.get("/analiticas", response_model=schemas.AnaliticaCoordinadorResponse)
def obtener_analiticas(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """
    Obtiene métricas analíticas avanzadas para el coordinador:
    - Comparativa de programas académicos.
    - Podio de los mejores practicantes (Leaderboard).
    - Desempeño y velocidad de validación de los tutores.
    """
    return crud.obtener_analitica_coordinador(db)


@router.post("/cargar-usuarios", status_code=201)
def cargar_usuarios_csv(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """
    Carga masiva de usuarios desde un archivo CSV.
    Campos requeridos en el CSV: nombre, correo, password, rol
    Campos opcionales: programa_academico, empresa_id
    El archivo debe contener cabeceras.
    """
    if not archivo.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .csv")
        
    try:
        contenido = archivo.file.read().decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error de decodificación. Asegúrese de que el archivo sea UTF-8.")
        
    lector = csv.DictReader(io.StringIO(contenido))
    
    # Validar cabeceras requeridas
    cabeceras_requeridas = {"nombre", "correo", "password", "rol"}
    if not cabeceras_requeridas.issubset(set(lector.fieldnames or [])):
        raise HTTPException(
            status_code=400, 
            detail=f"Faltan cabeceras requeridas en el CSV. Requeridas: {', '.join(cabeceras_requeridas)}. Encontradas: {lector.fieldnames}"
        )
        
    creados = 0
    errores = []
    
    for idx, fila in enumerate(lector, start=2):
        nombre = fila.get("nombre", "").strip()
        correo = fila.get("correo", "").strip()
        password = fila.get("password", "").strip()
        rol_str = fila.get("rol", "").strip().lower()
        programa = fila.get("programa_academico", "").strip() or None
        emp_id_str = fila.get("empresa_id", "").strip()
        
        empresa_id = None
        if emp_id_str and emp_id_str.isdigit():
            empresa_id = int(emp_id_str)
            
        if not nombre or not correo or not password or not rol_str:
            errores.append({"fila": idx, "correo": correo, "error": "Faltan campos obligatorios en esta fila."})
            continue
            
        # Validar rol
        try:
            rol = models.UserRole(rol_str)
        except ValueError:
            errores.append({"fila": idx, "correo": correo, "error": f"Rol inválido: '{rol_str}'"})
            continue
            
        # Validar si ya existe
        usuario_existente = crud.obtener_usuario_por_correo(db, correo)
        if usuario_existente:
            errores.append({"fila": idx, "correo": correo, "error": "El correo ya está registrado."})
            continue
            
        try:
            usuario_data = schemas.UsuarioCreate(
                nombre=nombre,
                correo=correo,
                password=password,
                rol=rol,
                programa_academico=programa,
                empresa_id=empresa_id
            )
            crud.crear_usuario(db, usuario_data)
            creados += 1
        except Exception as e:
            errores.append({"fila": idx, "correo": correo, "error": str(e)})
            
    return {
        "status": "success" if creados > 0 else "error",
        "mensaje": f"Se crearon {creados} usuarios con éxito.",
        "creados": creados,
        "errores": errores
    }


@router.get("/alertas-criticas")
def obtener_alertas_criticas(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """Obtiene alertas críticas para el dashboard del coordinador."""
    return crud.obtener_alertas_criticas(db)


@router.get("/exportar-practicas-csv")
def exportar_practicas_csv(
    db: Session = Depends(get_db),
    _=Depends(solo_coordinador)
):
    """
    Exporta un archivo CSV con el consolidado general de prácticas académicas.
    Compatible con Excel (UTF-8 con BOM).
    """
    output = io.StringIO()
    # Escribir el BOM (Byte Order Mark) para UTF-8 para que Excel lo detecte
    output.write('\ufeff')
    
    writer = csv.writer(output, delimiter=';')
    # Encabezados en español
    writer.writerow([
        "ID Práctica", "Estudiante", "Correo Estudiante", "Programa Académico",
        "Empresa", "NIT Empresa", "Tutor Académico", "Supervisor",
        "Horas Acumuladas", "Horas Requeridas", "% Avance", 
        "Calificación Promedio", "Estado Alerta", "Fecha Inicio", "Fecha Fin", "Estado Práctica"
    ])
    
    practicas = db.query(models.Practica).all()
    for p in practicas:
        est_nombre = p.estudiante.nombre if p.estudiante else "N/A"
        est_correo = p.estudiante.correo if p.estudiante else "N/A"
        est_programa = p.estudiante.programa_academico or "N/A"
        emp_nombre = p.empresa.nombre if p.empresa else "N/A"
        emp_nit = p.empresa.nit if p.empresa else "N/A"
        tut_nombre = p.tutor.nombre if p.tutor else "N/A"
        sup_nombre = p.supervisor.nombre if p.supervisor else "N/A"
        
        horas_req = p.horas_totales_requeridas or 320
        horas_acum = p.horas_acumuladas or 0.0
        porcentaje = round((horas_acum / horas_req) * 100, 1) if horas_req > 0 else 0.0
        
        f_ini = p.fecha_inicio.strftime("%Y-%m-%d") if p.fecha_inicio else "N/A"
        f_fin = p.fecha_fin.strftime("%Y-%m-%d") if p.fecha_fin else "N/A"
        
        writer.writerow([
            p.id, est_nombre, est_correo, est_programa,
            emp_nombre, emp_nit, tut_nombre, sup_nombre,
            horas_acum, horas_req, f"{porcentaje}%",
            p.calificacion, p.alerta_progreso.upper(), f_ini, f_fin, p.estado.upper()
        ])
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="consolidado_practicas_sipga.csv"'
    }
    
    from fastapi import Response
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)