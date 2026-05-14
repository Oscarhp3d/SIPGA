# Manual de Integración API - SIPGA v1.0

Este documento contiene los endpoints principales para que el equipo de Frontend conecte las interfaces.

##  Autenticación (Auth)
* **URL:** `POST /token`
* **Cuerpo:** `username` (correo) y `password`.
* **Uso:** Devuelve un `access_token`. Debe enviarse en el Header de las demás peticiones como: `Authorization: Bearer <token>`.

##  Usuarios y Roles
* **Crear Usuario:** `POST /usuarios/` (No requiere token para el registro inicial).
* **Roles disponibles:** `estudiante`, `tutor`, `supervisor`.

##  Seguimientos (El Core)
* **Reportar Horas (Estudiante):** `POST /seguimientos/`
    * Requiere: `practica_id`, `descripcion`, `horas_realizadas`.
* **Subir Evidencia:** `POST /seguimientos/{id}/subir-evidencia`
    * Formato: `multipart/form-data`.
    * Restricción: Solo PDF/JPG/PNG < 5MB.
* **Validar (Tutor):** `PATCH /seguimientos/{id}/validar-tutor`
* **Rechazar con Observaciones (Tutor):** `PATCH /seguimientos/{id}/rechazar?observaciones=texto`

## Reportes y Salida
* **Descargar PDF:** `GET /practicas/{id}/reporte-pdf`
    * Genera el documento oficial con firmas digitales y logos.

## Reglas de Seguridad (Auditoría)
1. **Validación de Roles:** Si un Estudiante intenta usar un endpoint de Tutor, recibirá un `403 Forbidden`.
2. **Soft-Delete:** Los registros eliminados no desaparecen de la DB, solo se marcan como ocultos por seguridad legal.
## Seguridad y Roles (RBAC)
- **Estudiante:** Crea seguimientos.
- **Tutor/Coordinador:** Valida/Rechaza y genera reportes.

## Endpoints de Misión Crítica
1. **Login (POST `/token`):** Devuelve el JWT con el rol incrustado.
2. **Crear Seguimiento (POST `/seguimientos/`):** - *Restricción:* Máximo 12h por reporte.
   - *Validación:* Descripción mín. 15 caracteres.
3. **Validar (PATCH `/seguimientos/{id}/validar`):**
   - *Auditoría:* Registra IP y ID del tutor automáticamente.
4. **Reporte PDF (GET `/reportes/pdf`):** Genera el formato oficial.