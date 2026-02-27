"""Application settings via pydantic-settings (reads .env)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """DrapeStudio configuration — loaded from environment / .env file."""

    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"

    # Database
    DATABASE_URL: str = "sqlite:///./drapestudio.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Google Gemini (legacy — kept for backward compatibility)
    GOOGLE_API_KEY: str = ""

    # OpenRouter (primary LLM provider)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-3.1-flash-image-preview"

    # Google Cloud Storage (production only)
    GCS_BUCKET_UPLOADS: str = ""
    GCS_BUCKET_OUTPUTS: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Storage mode
    STORAGE_BACKEND: str = "local"  # local | gcs

    # Cost controls
    DAILY_COST_LIMIT_USD: float = 10.00

    # Signed URL expiry
    UPLOAD_URL_EXPIRY_SECONDS: int = 900
    OUTPUT_URL_EXPIRY_SECONDS: int = 3600

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
