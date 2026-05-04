from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# --- CONFIGURACIÓN DE SQLALCHEMY PARA NEON ---
# Neon requiere SSL y un pool de conexiones especial
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"sslmode": "require"},  # Obligatorio para Neon
    pool_pre_ping=True,                   # Verifica conexión antes de usarla
    pool_recycle=300,                     # Recicla conexiones cada 5 minutos
)

# Fábrica de sesiones para interactuar con la DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

# Dependencia para obtener la sesión en los endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
