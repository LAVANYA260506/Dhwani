"""
Central application settings for Dhwani.

All values come from environment variables (see /.env.example) and are read
from `backend/.env`. Every other module should import `settings` from here
instead of calling os.getenv directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[1] = backend/, parents[2] = project root
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- General ----------
    APP_NAME: str = "Dhwani"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ---------- Backend ----------
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"
    SECRET_KEY: str = "change-me-to-a-long-random-string"

    # ---------- Database ----------
    DATABASE_URL: str = "sqlite:///./database/dhwani.db"

    # ---------- Document upload ----------
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_UPLOAD_TYPES: str = "application/pdf,image/jpeg,image/png"

    # ---------- Gnani voice ----------
    GNANI_API_KEY: str = ""
    GNANI_BASE_URL: str = "https://api.vachana.ai"
    GNANI_TIMEOUT_SECONDS: int = 20

    # Speech-to-text. prisma-v3.0 accepts a language list (Kannada + English).
    # Switch to prisma-v2.5 if your key does not have v3.0 access.
    GNANI_STT_MODEL: str = "prisma-v3.0"
    GNANI_STT_FORMAT: str = "transcribe"  # numbers written as digits

    # Text-to-speech. timbre-v3.0 voices speak all 10 languages, Kannada included.
    GNANI_TTS_MODEL: str = "timbre-v3.0"
    GNANI_TTS_VOICE: str = "Lakshmi"
    GNANI_TTS_SPEED: float = 1.0
    GNANI_TTS_SAMPLE_RATE: int = 24000
    GNANI_TTS_CONTAINER: str = "mp3"  # plays directly in the browser <audio> tag

    # ---------- LlamaParse ----------
    LLAMA_CLOUD_API_KEY: str = ""
    LLAMAPARSE_TIMEOUT_SECONDS: int = 60

    # ---------- LLM agent (Gemini) ----------
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash"
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    LLM_TIMEOUT_SECONDS: int = 30

    # ---------- Derived values ----------
    @field_validator("DATABASE_URL")
    @classmethod
    def _resolve_sqlite_path(cls, value: str) -> str:
        """Make a relative SQLite path absolute (relative to project root)
        so the DB always lands in dhwani/database/ no matter where the
        server is started from."""
        prefix = "sqlite:///"
        if value.startswith(prefix) and not value.startswith("sqlite:////"):
            relative = value[len(prefix):]
            db_path = (PROJECT_ROOT / relative).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"{prefix}{db_path.as_posix()}"
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_upload_types_list(self) -> list[str]:
        return [t.strip() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def upload_dir_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()