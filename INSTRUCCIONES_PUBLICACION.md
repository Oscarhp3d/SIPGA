# 🚀 Guía de Publicación para SIPGA

He configurado todo para que puedas publicar el backend y tus compañeros solo tengan que preocuparse por el diseño del frontend.

##  Lo que ya hice:
1. **Esquema en Supabase**: Ya creé todas las tablas y tipos (Enums) en tu proyecto de Supabase usando el script `dump_schema.py`.
2. **Archivos de Despliegue**: Creé `backend/Procfile` y `render.yaml` en la raíz para que puedas subirlo a **Render** fácilmente.
3. **Optimización de Dependencias**: Corregí `backend/requirements.txt` para incluir `gunicorn` y arreglar errores de formato.
4. **Preparación del Frontend**: Modifiqué `frontend/index.html` para que detecte si debe conectarse al backend local o al de producción.

---

##  Pasos para completar la publicación:

### 1. Obtener la URL de Supabase
Ve a tu proyecto de Supabase y busca:
*   **Project Settings** > **Database**.
*   Busca **Connection String** y copia la opción de **URI**.
*   Se verá algo como: `postgresql://postgres:[TU-PASSWORD]@db.xxxx.supabase.co:5432/postgres`
    *   *Nota: Reemplaza `[TU-PASSWORD]` con la contraseña que definiste al crear el proyecto.*

### 2. Desplegar el Backend en Render
1. Crea una cuenta en [render.com](https://render.com).
2. Conecta tu repositorio de GitHub.
3. Elige **"Blueprint"** (esto leerá el archivo `render.yaml` que te creé).
4. En la configuración de Render, te pedirá la `DATABASE_URL`. Pega la URI de Supabase.
5. Render generará una URL pública (ej: `https://sipga-backend.onrender.com`).

### 3. Actualizar la URL en el Frontend
En `frontend/index.html`, busca la línea 46 y cambia la URL por la que te dio Render:

```javascript
: "https://sipga-backend.onrender.com"; 
```

### 4. ¿Cómo trabajarán tus compañeros?
Cuando ellos clonen el repositorio:
1. **No necesitan configurar nada del backend.**
2. Solo abren `frontend/index.html`.
3. El frontend se conectará automáticamente a la API que tú ya dejaste "viva" en internet.
4. Pueden dedicarse 100% al diseño sin tocar una sola línea de código Python.

---

**¡Listo! Ya tienes una arquitectura profesional: Base de Datos en Supabase y API en la nube.**
