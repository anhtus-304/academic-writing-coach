from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # Project & API settings
    PROJECT_NAME: str
    API_V1_STR: str
    APP_ENV: str
    ENVIRONMENT: str
    DEBUG: bool

    # Database configuration
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    # OpenRouter LLM Configuration
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str
    DEFAULT_MODEL: str
    FALLBACK_MODEL: str

    # Security & JWT settings
    JWT_SECRET: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_EXPIRATION_MINUTES: int
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str

    # CORS settings
    BACKEND_CORS_ORIGINS: List[str]

    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env", str(BASE_DIR / ".env")],
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

