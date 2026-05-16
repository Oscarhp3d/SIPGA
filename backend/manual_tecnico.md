# Manual de Integración API - SIPGA v1.0

Este documento contiene los endpoints principales para que el equipo de Frontend conecte las interfaces.

##  Autenticación (Auth)
* **URL:** `POST /api/v1/auth/login`
* **Cuerpo:** `correo` y `password`.
* **Uso:** Devuelve un `access_token`. Debe enviarse en el Header de las demás peticiones como: `Authorization: Bearer <token>`.

##  Usuarios y Roles
* **Me (Usuario Actual):** `GET /api/v1/usuarios/me`
* **Crear Usuario:** `POST /api/v1/usuarios/` (Requiere rol de Coordinador).
* **Roles disponibles:** `estudiante`, `tutor`, `supervisor`, `coordinador`.

##  Seguimientos (El Core)
* **Reportar Horas (Estudiante):** `POST /api/v1/seguimientos/`
    * Requiere: `practica_id`, `descripcion`, `horas_realizadas`, `fecha_actividad`.
* **Subir Evidencia:** `POST /api/v1/seguimientos/{id}/subir-evidencia`
    * Formato: `multipart/form-data` con campo `archivo`.
    * Restricción: Solo PDF/JPG/PNG < 5MB.
* **Validar Seguimiento (Tutor/Supervisor/Coordinador):** `PATCH /api/v1/seguimientos/{id}/validar`
    * Cuerpo: `{ "estado": "aprobado", "observaciones_tutor": "..." }`

##  Prácticas
* **Crear Práctica:** `POST /api/v1/practicas/` (Solo Coordinador).
* **Listar Mis Prácticas:** `GET /api/v1/practicas/mis`
* **Actualizar Estado:** `PATCH /api/v1/practicas/{id}` (Activar o Finalizar).

## Reportes y Salida
* **Descargar PDF:** `GET /api/v1/practicas/{id}/reporte-pdf`
    * Genera el documento oficial con el consolidado de horas y actividades.

## Reglas de Seguridad (Auditoría)
1. **Validación de Roles:** Si un Estudiante intenta usar un endpoint de Tutor, recibirá un `403 Forbidden`.
2. **Soft-Delete:** Los registros eliminados no desaparecen de la DB, solo se marcan como ocultos (`is_deleted = True`) por seguridad legal.
3. **Control de Horas:** Se actualiza automáticamente el campo `horas_acumuladas` en la tabla `practicas` al aprobar un seguimiento.
4. **Auditoría:** Cada acción crítica registra automáticamente la IP del actor en la tabla `logs_auditoria`.