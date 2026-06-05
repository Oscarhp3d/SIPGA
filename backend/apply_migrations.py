import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
import models
from sqlalchemy import text

def run_migrations():
    print("Conectando a la base de datos y aplicando alteraciones de columnas...")
    
    queries = [
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS fecha_inicio_convenio TIMESTAMP;",
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS fecha_fin_convenio TIMESTAMP;",
        "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cupos_totales INTEGER DEFAULT 0;",
        "ALTER TABLE practicas ADD COLUMN IF NOT EXISTS codigo_certificado VARCHAR(50) UNIQUE;",
        "ALTER TABLE seguimientos ADD COLUMN IF NOT EXISTS fecha_envio TIMESTAMP;",
        "ALTER TABLE seguimientos ADD COLUMN IF NOT EXISTS fecha_preaprobacion TIMESTAMP;",
        "ALTER TABLE seguimientos ADD COLUMN IF NOT EXISTS fecha_aprobacion TIMESTAMP;"
    ]
    
    with engine.begin() as conn:
        for query in queries:
            try:
                print(f"Ejecutando: {query}")
                conn.execute(text(query))
            except Exception as e:
                print(f"Error al ejecutar '{query}': {e}")
                raise e
            
    print("Creando nuevas tablas si no existen...")
    Base.metadata.create_all(bind=engine)
    print("¡Migración completada con éxito!")

if __name__ == "__main__":
    run_migrations()
