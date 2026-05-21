import os
import pytest
from playwright.sync_api import Page, expect

# Configuración de URLs basada en servidor local de FastAPI
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/login.html"
DASHBOARD_URL = f"{BASE_URL}/dashboard.html"

# Credenciales de prueba (basadas en seed_data.py)
USERS = {
    "coordinador": {"email": "admin@sipga.edu.co", "pass": "admin123", "name": "Admin Coordinador"},
    "tutor": {"email": "jbenitez@sipga.edu.co", "pass": "admin123", "name": "Dr. Julio Benitez"},
    "supervisor": {"email": "carlos@empresa.com", "pass": "admin123", "name": "Carlos Supervisor"},
    "estudiante": {"email": "estudiante@sipga.edu.co", "pass": "admin123", "name": "Estudiante Prueba"}
}

def test_demo_completa_roles(page: Page):
    """
    Test E2E que automatiza el flujo completo de la demostración para la presentación del proyecto.
    Cubre: Estudiante -> Tutor -> Supervisor -> Coordinador
    """
    
    # =========================================================================
    # ACTO 1: EL ESTUDIANTE REGISTRA HORAS Y SUBE EVIDENCIA
    # =========================================================================
    print("\n--- Iniciando Acto 1: Estudiante ---")
    
    # Habilitar logging del navegador para diagnóstico
    page.on("console", lambda msg: print(f"[Browser Console] {msg.text}"))
    page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))
    
    page.goto(LOGIN_URL)
    page.locator("input[type='email']").fill(USERS["estudiante"]["email"])
    page.locator("input[type='password']").fill(USERS["estudiante"]["pass"])
    page.locator("button:has-text('Iniciar Sesión')").click()
    
    # Esperar redirección al dashboard
    page.wait_for_url("**/dashboard.html")
    expect(page.locator("#topbarNombre")).to_contain_text(USERS["estudiante"]["name"])
    print("[Estudiante] Sesión iniciada con éxito.")
    
    # Ir a la sección Log de Horas
    page.locator("a[data-page='log']").click()
    expect(page.locator("h1:has-text('Log de Horas')")).to_be_visible()
    
    # Abrir modal para registrar horas
    page.locator("button:has-text('Registrar Horas')").click()
    expect(page.locator("#modalTitulo")).to_have_text("Registrar Actividad")
    
    # Diligenciar actividad
    from datetime import datetime, timedelta
    import random
    unique_suffix = f"{datetime.now().strftime('%m%d%H%M%S')}_{random.randint(1000, 9999)}"
    descripcion_actividad = f"Demo Playwright {unique_suffix}"
    page.locator("#logDesc").fill(descripcion_actividad)
    page.locator("#logHoras").fill("6.0")
    
    # Definir fecha de ayer formateada YYYY-MM-DD para evitar errores de hora futura en el validador del backend
    ayer_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    page.locator("#logFecha").fill(ayer_str)
    
    # Guardar actividad
    page.locator("button:has-text('Guardar Actividad')").click()
    
    # Esperar Toast de éxito y cierre de modal
    try:
        page.wait_for_selector("text=Actividad registrada correctamente", timeout=8000)
        print("[Estudiante] Actividad de 6 horas registrada exitosamente.")
    except Exception as e:
        error_element = page.locator("#logError")
        visible_error = error_element.inner_text() if error_element.is_visible() else "Ningún error visible en pantalla"
        print(f"[ERROR DE REGISTRO] Falló el guardado de la actividad. Mensaje en pantalla: '{visible_error}'")
        raise e
    
    # Cerrar sesión del estudiante
    page.locator("#btnLogout").click()
    page.wait_for_url("**/login.html")
    print("[Estudiante] Sesión cerrada.")
    
    # =========================================================================
    # ACTO 2: EL SUPERVISOR DE EMPRESA PRE-APRUEBA LA ACTIVIDAD
    # =========================================================================
    print("\n--- Iniciando Acto 2: Supervisor de Empresa ---")
    page.goto(LOGIN_URL)
    page.locator("input[type='email']").fill(USERS["supervisor"]["email"])
    page.locator("input[type='password']").fill(USERS["supervisor"]["pass"])
    page.locator("button:has-text('Iniciar Sesión')").click()
    
    page.wait_for_url("**/dashboard.html")
    expect(page.locator("#topbarNombre")).to_contain_text(USERS["supervisor"]["name"])
    print("[Supervisor] Sesión iniciada con éxito.")
    
    # Ir a sección validación
    page.locator("a[data-page='validacion']").click()
    expect(page.locator("h1:has-text('Validación de Actividades')")).to_be_visible()
    
    # Localizar la fila del estudiante y hacer clic en Aprobar
    fila_actividad_sup = page.locator("#tablaValidacion tr", has_text=USERS["estudiante"]["name"]).filter(has_text=descripcion_actividad[:25])
    expect(fila_actividad_sup).to_be_visible()
    fila_actividad_sup.locator("button:has-text('Aprobar')").click()
    
    page.wait_for_timeout(1000)
    print("[Supervisor] Actividad del estudiante pre-aprobada (estado: pendiente_tutor).")
    
    # Cerrar sesión
    page.locator("#btnLogout").click()
    page.wait_for_url("**/login.html")
    print("[Supervisor] Sesión cerrada.")
    
    # =========================================================================
    # ACTO 3: EL TUTOR INGRESA Y APRUEBA LA ACTIVIDAD DEFINITIVAMENTE
    # =========================================================================
    print("\n--- Iniciando Acto 3: Tutor Académico ---")
    page.goto(LOGIN_URL)
    page.locator("input[type='email']").fill(USERS["tutor"]["email"])
    page.locator("input[type='password']").fill(USERS["tutor"]["pass"])
    page.locator("button:has-text('Iniciar Sesión')").click()
    
    page.wait_for_url("**/dashboard.html")
    expect(page.locator("#topbarNombre")).to_contain_text(USERS["tutor"]["name"])
    print("[Tutor] Sesión iniciada con éxito.")
    
    # Ir a sección validación
    page.locator("a[data-page='validacion']").click()
    expect(page.locator("h1:has-text('Validación de Actividades')")).to_be_visible()
    
    # Localizar la fila del estudiante y hacer clic en Aprobar
    fila_actividad = page.locator("#tablaValidacion tr", has_text=USERS["estudiante"]["name"]).filter(has_text=descripcion_actividad[:25])
    expect(fila_actividad).to_be_visible()
    
    # Hacer clic en el botón de aprobar específico de esa fila
    fila_actividad.locator("button:has-text('Aprobar')").click()
    
    # Esperar actualización
    page.wait_for_timeout(1000)
    print("[Tutor] Actividad del estudiante aprobada con éxito.")
    
    # Cerrar sesión
    page.locator("#btnLogout").click()
    page.wait_for_url("**/login.html")
    print("[Tutor] Sesión cerrada.")
    
    # =========================================================================
    # ACTO 3: EL SUPERVISOR VERIFICA EL ESTADO
    # =========================================================================
    print("\n--- Iniciando Acto 3: Supervisor de Empresa ---")
    page.goto(LOGIN_URL)
    page.locator("input[type='email']").fill(USERS["supervisor"]["email"])
    page.locator("input[type='password']").fill(USERS["supervisor"]["pass"])
    page.locator("button:has-text('Iniciar Sesión')").click()
    
    page.wait_for_url("**/dashboard.html")
    expect(page.locator("#topbarNombre")).to_contain_text(USERS["supervisor"]["name"])
    print("[Supervisor] Sesión iniciada con éxito.")
    
    # El supervisor puede ver la validación y el dashboard adaptado (sin ver reportes ni usuarios globales)
    expect(page.locator("a[data-page='usuarios']")).not_to_be_visible()
    expect(page.locator("a[data-page='empresas']")).not_to_be_visible()
    expect(page.locator("a[data-page='reportes']")).not_to_be_visible()
    print("[Supervisor] Restricciones de seguridad por rol validadas.")
    
    # Cerrar sesión
    page.locator("#btnLogout").click()
    page.wait_for_url("**/login.html")
    print("[Supervisor] Sesión cerrada.")
    
    # =========================================================================
    # ACTO 4: EL COORDINADOR CREA UN NUEVO USUARIO Y VALIDA EL DASHBOARD
    # =========================================================================
    print("\n--- Iniciando Acto 4: Coordinador General ---")
    page.goto(LOGIN_URL)
    page.locator("input[type='email']").fill(USERS["coordinador"]["email"])
    page.locator("input[type='password']").fill(USERS["coordinador"]["pass"])
    page.locator("button:has-text('Iniciar Sesión')").click()
    
    page.wait_for_url("**/dashboard.html")
    expect(page.locator("#topbarNombre")).to_contain_text(USERS["coordinador"]["name"])
    print("[Coordinador] Sesión iniciada con éxito.")
    
    # Ir a la sección Usuarios
    page.locator("a[data-page='usuarios']").click()
    expect(page.locator("h1:has-text('Gestión de Usuarios')")).to_be_visible()
    
    # Registrar un nuevo estudiante
    page.locator("button#btnNuevoUsuario").click()
    expect(page.locator("#modalTitulo")).to_have_text("Nuevo Usuario")
    
    nuevo_correo = f"demo_alumno_{datetime.now().strftime('%M%S')}@sipga.edu.co"
    page.locator("#nuNombre").fill("Demo Alumno Automatizado")
    page.locator("#nuCorreo").fill(nuevo_correo)
    page.locator("#nuPassword").fill("Demo12345*")
    page.locator("#nuRol").select_option("estudiante")
    page.locator("#nuPrograma").fill("Ingeniería de Sistemas")
    page.locator("#nuAceptaDatos").check()
    
    # Guardar
    page.locator("#btnGuardarUsuario").click()
    try:
        page.wait_for_selector("text=creado correctamente", timeout=8000)
        print(f"[Coordinador] Nuevo estudiante registrado: {nuevo_correo}")
    except Exception as e:
        error_element = page.locator("#nuError")
        visible_error = error_element.inner_text() if error_element.is_visible() else "Ningún error visible"
        print(f"[ERROR AL CREAR USUARIO] Mensaje en pantalla: '{visible_error}'")
        raise e
    
    # Ir a Reportes
    page.locator("a[data-page='reportes']").click()
    expect(page.locator("h1:has-text('Reportes')")).to_be_visible()
    
    # Descargar el reporte PDF de la primera práctica de la tabla
    with page.expect_download() as download_info:
        page.locator("button:has-text('PDF')").first.click()
    download = download_info.value
    assert download.suggested_filename.startswith("Reporte_SIPGA_")
    print(f"[Coordinador] Reporte PDF descargado con éxito: {download.suggested_filename}")
    
    # Cerrar sesión final
    page.locator("#btnLogout").click()
    page.wait_for_url("**/login.html")
    print("[Coordinador] Demo automatizada completada con éxito.")
