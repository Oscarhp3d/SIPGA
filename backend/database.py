from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# --- CONFIGURACIÓN DE SQLALCHEMY ---
# Creamos el motor de la base de datos usando la URL de la configuración
engine = create_engine(settings.DATABASE_URL)

# Creamos la fábrica de sesiones para interactuar con la DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos (Tablas de la base de datos)
Base = declarative_base()

# Dependencia para obtener la sesión en los endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

