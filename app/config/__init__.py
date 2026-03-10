"""App configuration package.

Re-exports `settings` from this package so that:
  `from app.config import settings`
works correctly even though app/config/ is a package directory
that shadows app/config.py on case-sensitive filesystems (Linux/Docker).
"""

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
    STORAGE_ROOT: str = "./storage"  # local filesystem root for uploads/outputs

    # Cost controls
    DAILY_COST_LIMIT_USD: float = 10.00

    # Signed URL expiry
    UPLOAD_URL_EXPIRY_SECONDS: int = 900
    OUTPUT_URL_EXPIRY_SECONDS: int = 3600

    # JWT authentication
    JWT_SECRET: str = "change-me-jwt-secret-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440   # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth (Sign in with Google)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8888/auth/callback"

    # Notify.lk SMS (Sri Lanka) — legacy, kept for backward compat
    NOTIFY_LK_USER_ID: str = ""
    NOTIFY_LK_API_KEY: str = ""
    NOTIFY_LK_SENDER_ID: str = "NotifyDEMO"

    # PayHere payment gateway (Sri Lanka)
    PAYHERE_MERCHANT_ID: str = ""
    PAYHERE_MERCHANT_SECRET: str = ""
    PAYHERE_SANDBOX: bool = True   # True = sandbox, False = production
    BASE_URL: str = "http://localhost:8888"  # Used for PayHere callback URLs

    # Web Push / VAPID keys (generate with: py -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.private_pem().decode()); print(v.public_key.decode())")
    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "admin@drapestudio.lk"

    # Google Analytics 4
    GA4_MEASUREMENT_ID: str = ""  # e.g. G-XXXXXXXXXX

    # Sentry error tracking
    SENTRY_DSN: str = ""           # Server-side DSN
    SENTRY_DSN_JS: str = ""        # Client-side DSN (can be same as server DSN)

    # App versioning (used in Sentry release tag and cache-busting)
    APP_VERSION: str = "2.0.0"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
