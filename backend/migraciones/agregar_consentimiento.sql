-- ============================================================
-- MIGRACIÓN: Consentimiento informado — Ley 1581/2012
-- Aplicar sobre la base de datos PostgreSQL de SIPGA
-- Fecha: 2026
-- ============================================================
-- INSTRUCCIONES:
--   Conectarse a la BD y ejecutar este script completo.
--   Es seguro correrlo más de una vez (usa IF NOT EXISTS).
-- ============================================================

-- 1. Agregar columna de aceptación (boolean, no nulo, default false
--    para filas existentes que luego se actualizarán en el paso 3)
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS acepto_politica BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Agregar marca de tiempo del consentimiento (nullable)
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS fecha_consentimiento TIMESTAMP WITHOUT TIME ZONE;

-- 3. Agregar versión del documento de política (nullable)
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS version_politica VARCHAR(20);

-- 4. Regularizar usuarios existentes:
--    Los usuarios que ya están en el sistema fueron creados
--    por el coordinador, por lo tanto se consideran con consentimiento
--    institucional registrado en la fecha de aplicación de esta migración.
UPDATE usuarios
SET
    acepto_politica      = TRUE,
    fecha_consentimiento = NOW(),
    version_politica     = 'v1.0'
WHERE acepto_politica = FALSE;

-- 5. Verificación: todos deben tener acepto_politica = TRUE después
--    de la regularización. Si alguna fila queda en FALSE, revisar
--    manualmente antes de poner en producción.
SELECT
    COUNT(*) FILTER (WHERE acepto_politica = TRUE)  AS con_consentimiento,
    COUNT(*) FILTER (WHERE acepto_politica = FALSE) AS sin_consentimiento
FROM usuarios;
