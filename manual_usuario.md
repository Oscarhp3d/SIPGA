# Manual de Usuario - SIPGA v1.0
## Sistema de Información para Gestión de Prácticas Académicas

Bienvenido al manual de usuario de **SIPGA**. Este documento le guiará a través de las funcionalidades del sistema según su rol asignado, detallando los nuevos módulos y mejoras implementadas para mejorar la trazabilidad, transparencia y automatización del proceso de prácticas.

---

## 🔑 1. Credenciales de Acceso Rápido (Entorno de Pruebas)
Para validar el sistema con datos reales precargados en la base de datos PostgreSQL, puede iniciar sesión utilizando las siguientes cuentas (contraseña común: `admin123`):

*   **Coordinador Académico:** `admin@sipga.edu.co`
*   **Tutor Académico:** `jbenitez@sipga.edu.co`
*   **Supervisor de Empresa:** `carlos@empresa.com`
*   **Estudiantes:** `estudiante@sipga.edu.co` y `oscar@sipga.edu.co`

---

## 💻 2. Módulos y Funcionalidades por Rol

### 🎓 2.1. Portal del Estudiante
El estudiante dispone de una interfaz intuitiva para documentar su proceso diario:

1.  **Dashboard con Semáforo de Progreso:**
    *   Muestra una barra de avance porcentual en tiempo real.
    *   **Semáforo de Actividad:** El sistema alerta visualmente si hay inactividad (más de 7 días sin reportar) o si el estudiante se encuentra en "Retraso" (proyección matemática basada en la fecha de finalización y el promedio de horas reportadas).
2.  **Registro Diario con Límites Estrictos:**
    *   Permite ingresar la descripción, fecha y duración de las actividades.
    *   **Validación Inteligente:** El backend no permite registrar más de **8 horas diarias** en un mismo día ni superar **48 horas semanales** acumuladas en los últimos 7 días, previniendo reportes fraudulentos.
3.  **Historial de Versiones en Correcciones:**
    *   Si un reporte es rechazado por el Tutor o Supervisor, el estudiante puede corregir la descripción u horas y volver a enviarlo.
    *   El sistema guarda un historial inmutable del texto y horas originales en la base de datos antes de aplicar los cambios.
4.  **Carga de Evidencias:**
    *   Permite adjuntar un archivo de soporte (PDF o Imagen) para justificar las horas reportadas.
5.  **Descarga del Certificado Oficial:**
    *   Una vez que el estudiante alcanza el 100% de sus horas requeridas y la práctica es marcada como "Finalizada", se habilita un botón para descargar el certificado PDF oficial que contiene un código de seguridad único y un código QR vectorial.

---

### 👨‍🏫 2.2. Portal del Tutor Académico
El tutor supervisa el cumplimiento pedagógico de los estudiantes asignados a su programa académico:

1.  **Visor de Evidencias Integrado:**
    *   Permite inspeccionar documentos e imágenes de soporte directamente dentro de un modal interactivo en el navegador, **eliminando la necesidad de descargar archivos** a su equipo.
2.  **Aprobación y Pre-aprobación:**
    *   El tutor puede pre-aprobar o aprobar de forma definitiva las horas reportadas por los estudiantes. Cada cambio registra marcas de tiempo precisas para medir la velocidad de respuesta.
3.  **Rúbricas de Evaluación 360°:**
    *   Permite calificar el desempeño del estudiante mediante una rúbrica estructurada que evalúa: *Conocimiento Técnico*, *Puntualidad*, *Proactividad* y *Comunicación*.
    *   El promedio de estas rúbricas constituirá la nota final de la práctica.

---

### 🏢 2.3. Portal del Supervisor de Empresa
El supervisor valida el desempeño del practicante directamente en el sitio de trabajo:

1.  **Validación Técnica de Actividades:**
    *   Acceso a la bandeja de seguimientos exclusivos del estudiante asignado a su empresa.
    *   Uso del visor de evidencias en línea para validar las tareas ejecutadas.
2.  **Rúbricas del Sector Externo:**
    *   Ingreso de calificaciones cuantitativas (escala 1.0 a 5.0) en los criterios definidos, aportando observaciones cualitativas que ayudan al crecimiento profesional del estudiante.

---

### 🏛️ 2.4. Portal del Coordinador Académico (Módulo Principal de Control)
El coordinador académico dispone de las herramientas de administración, auditoría y alertas críticas más potentes:

1.  **Torre de Control de Alertas Críticas (Novedad):**
    *   En la parte superior del Dashboard del coordinador, se despliega una barra de monitoreo en caliente dividida en 4 paneles:
        *   **Retraso en Avance:** Lista los estudiantes cuyo rendimiento proyecta que no culminarán sus horas en la fecha pactada.
        *   **Inactividad:** Muestra a los practicantes que llevan más de 7 días sin subir ningún reporte de horas.
        *   **Convenios por Vencer:** Avisa qué empresas aliadas tienen convenios por expirar en menos de 60 días o que ya están vencidos.
        *   **Demora en Validación:** Identifica reportes de estudiantes en estado `enviado` o `pendiente_tutor` que llevan más de 5 días en espera de revisión por el supervisor o tutor.
2.  **Semáforo de Convenios y Cupos en Empresas (Novedad):**
    *   En la pestaña **Empresas**, la tabla muestra dos nuevas columnas:
        *   **Convenio:** Badge dinámico de color **Verde** (Vigente con más de 60 días), **Amarillo** (Por vencer en menos de 60 días) o **Rojo** (Vencido o sin registrar).
        *   **Cupos:** Relación numérica de plazas ocupadas frente a las totales (ej. `2 / 5` cupos ocupados). Evita la sobre-asignación de practicantes.
    *   El modal de **Nueva Empresa** ahora incluye campos obligatorios para definir la *Fecha de Inicio*, *Fecha de Cierre de Convenio* y *Cupos Totales*.
3.  **Exportación de Consolidado a CSV (Novedad):**
    *   En la esquina superior derecha del Dashboard, el coordinador dispone del botón **"Exportar Consolidado (CSV)"**.
    *   Al hacer clic, descarga una hoja de cálculo formateada con delimitador punto y coma (`;`) y BOM de UTF-8 (compatible con Microsoft Excel) que condensa el estado legal y de horas de todas las prácticas del sistema.
4.  **Carga Masiva de Usuarios (CSV):**
    *   Permite registrar masivamente a Estudiantes, Tutores y Supervisores subiendo un único archivo CSV.
5.  **Generación de Documentos Oficiales:**
    *   Genera el acta de cierre en PDF usando ReportLab con firmas de las 3 partes (Coordinador, Supervisor, Tutor) y código QR vectorial de seguridad.

---

## 🔍 3. Módulo de Verificación Pública
Cualquier tercero (entidades auditoras o futuros empleadores) puede verificar la validez de un certificado emitido por SIPGA:

1.  Escanee el código QR ubicado en la esquina inferior del certificado de finalización PDF, o ingrese manualmente a la página de verificación pública.
2.  Introduzca el código único del certificado.
3.  El sistema consultará de forma segura la base de datos de SIPGA y mostrará el nombre del estudiante, programa académico, horas cumplidas, nota definitiva de la práctica y firmas institucionales registradas.

---

## ❓ 4. Preguntas Frecuentes (FAQ)

**¿Qué indica el estado "Retraso" en mi práctica?**
Significa que si continúas reportando horas al ritmo actual, no lograrás completar las horas requeridas antes de la fecha de finalización pactada. Te sugerimos aumentar la intensidad horaria (sin superar las 8h diarias) o solicitar una prórroga.

**¿Qué pasa si subo un CSV con correos repetidos?**
El backend identificará los duplicados y evitará insertarlos de nuevo, indicando en el registro de auditoría las inserciones exitosas y las omitidas de forma segura.

**¿El certificado PDF con QR es seguro?**
Sí, el código QR genera un enlace firmado dinámico con el dominio de la institución, direccionando al verificador oficial público donde se validan los metadatos relacionales guardados en Neon PostgreSQL.
