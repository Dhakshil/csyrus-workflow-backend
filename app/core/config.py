from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Pydantic validates types at startup. If a required var is missing
    or has the wrong type, the app fails fast instead of crashing later
    when a request hits a missing config value.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Csyrus Workflow"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: str
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 1440


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    lru_cache means we parse .env only once per process. Without it,
    every request would re-read the file from disk.
    """
    return Settings()


settings = get_settings()