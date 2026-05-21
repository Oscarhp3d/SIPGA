# SIPGA — Sistema de Gestión de Prácticas Académicas

Sistema integral para el seguimiento, control y validación de horas de prácticas académicas, cumpliendo con la Ley 1581 de 2012 (Tratamiento de Datos Personales en Colombia).

## 🚀 Guía de Inicio Rápido

### Requisitos
* Python 3.9+
* Node.js (opcional, para live server o herramientas de testing)
* Playwright (para pruebas E2E/UI)

### Instalación
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Oscarhp3d/SIPGA.git
   cd SIPGA
   ```
2. Crear un entorno virtual e instalar dependencias del backend:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate

   pip install -r backend/requirements.txt
   ```
3. Configurar las variables de entorno:
   Crea un archivo `.env` en el directorio `backend` con las variables de base de datos (por defecto utiliza SQLite localmente).
4. Inicializar la base de datos local e inyectar semillas de prueba:
   ```bash
   python backend/seed_data.py
   ```
5. Iniciar el servidor backend de desarrollo:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
6. Iniciar el frontend:
   Abre el archivo `frontend/login.html` directamente en tu navegador o utilizando un servidor web local (como Live Server o `python -m http.server`).

## 📚 Documentación del Proyecto
* [Manual de Usuario](manual_usuario.md) — Guía detallada para Estudiantes, Tutores y Coordinadores.
* [Manual Técnico](backend/manual_tecnico.md) — Arquitectura, modelo de datos relacional y configuración del servidor API.

## ✨ Características Principales
* **RBAC (Control de Acceso Basado en Roles):** Vistas y permisos diferenciados para Coordinador, Tutor, Supervisor y Estudiante.
* **Seguridad y Cifrado:** Autenticación robusta basada en JWT y cifrado de contraseñas con bcrypt.
* **Gestión de Consentimiento:** Registro formal y marca de tiempo del consentimiento de tratamiento de datos personales conforme a la legislación nacional colombiana (Ley 1581/2012).
* **Generación de Reportes PDF:** Descarga de reportes detallados del avance y estado de prácticas en formato PDF.
* **Auditoría del Sistema:** Log inmutable de acciones críticas con registro de la IP del usuario.
* **Diseño Responsive:** Interfaz moderna y adaptativa basada en TailwindCSS.
