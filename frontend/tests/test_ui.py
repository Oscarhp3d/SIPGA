import os
import pytest
from playwright.sync_api import Page, expect

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGIN_URL = f"file:///{os.path.join(BASE_DIR, 'login.html').replace(chr(92), '/')}"
DASHBOARD_URL = f"file:///{os.path.join(BASE_DIR, 'dashboard.html').replace(chr(92), '/')}"

def test_login_renderiza_correctamente(page: Page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    expect(page).to_have_title("SIPGA — Iniciar Sesión")
    expect(page.locator("input[type='email']")).to_be_visible()
    expect(page.locator("input[type='password']")).to_be_visible()

def test_login_fallido_mock(page: Page):
    def handle_route(route):
        route.fulfill(status=401, json={"detail": "Credenciales inválidas"})
    page.route("**/api/v1/auth/token", handle_route)
    
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.locator("input[type='email']").fill("admin@sipga.com")
    page.locator("input[type='password']").fill("clave")
    page.locator("button", has_text="Iniciar Sesión").click()
    
    expect(page.locator("#errorMsg")).to_have_text("Credenciales inválidas", timeout=5000)

def test_dashboard_proteccion_rutas(page: Page):
    page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
    page.wait_for_url("**/login.html**", timeout=5000)

def test_dashboard_doble_submit(page: Page):
    page.add_init_script("localStorage.setItem('token', 'fake'); localStorage.setItem('user', JSON.stringify({rol: 'coordinador', id: '1'}));")
    page.route("**/api/v1/usuarios/me", lambda route: route.fulfill(status=200, json={"id": "1", "rol": "coordinador", "nombre": "Admin"}))
    page.route("**/api/v1/coordinador/dashboard", lambda route: route.fulfill(status=200, json={}))
    
    page.goto(DASHBOARD_URL, wait_until="domcontentloaded")
    
    # Simular que hacemos clic en el tab de Usuarios para que se muestre
    page.locator("a[data-page='usuarios']").click()
    
    page.locator("button#btnNuevoUsuario").click()
    page.locator("#nuNombre").fill("Usuario Test")
    page.locator("#nuCorreo").fill("test@sipga.com")
    page.locator("#nuPassword").fill("Password123")
    
    btn_guardar = page.locator("button[onclick='crearUsuario()']")
    btn_guardar.click()
    
    expect(btn_guardar).to_be_disabled()
    expect(btn_guardar).to_have_text("Guardando...")
