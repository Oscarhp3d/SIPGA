import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "SIPRA API"
    VERSION: str = "1.2.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    ALLOWED_ORIGINS: Any = ["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000"]
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return ["http://localhost:5500", "http://127.0.0.1:5500"]
    
    # File Storage
    UPLOAD_DIR: str = "evidencias"
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        case_sensitive=True
    )

settings = Settings()