import os
from dotenv import load_dotenv # Cargador oficial de variables de entorno
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- CONFIGURACIÓN DE ENTORNO ---
# Carga las variables definidas
load_dotenv() 


SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# --- CONFIGURACIÓN DE SQLALCHEMY ---
# Creamos el motor de la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL)

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
