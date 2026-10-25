import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # --------------------------------------------------
    # Environment
    # --------------------------------------------------

    # "production" turns missing secrets into startup errors.
    APP_ENV: str = "development"

    # --------------------------------------------------
    # Database (plain PostgreSQL)
    # --------------------------------------------------

    # SQLAlchemy URL using the psycopg v3 driver, e.g.
    # postgresql+psycopg://user:pass@host:5432/trendy
    DATABASE_URL: str = "postgresql+psycopg://trendy:trendy@localhost:5432/trendy"

    # Apply db/migrations/*.sql automatically when the API starts.
    RUN_MIGRATIONS_ON_STARTUP: bool = False

    # --------------------------------------------------
    # Object storage (S3-compatible, e.g. MinIO)
    # --------------------------------------------------

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    # Browser-facing base URL; public URLs are "{S3_PUBLIC_BASE_URL}/{bucket}/{path}".
    S3_PUBLIC_BASE_URL: str = "http://localhost:9000"

    STORAGE_BUCKET: str = "brand-assets"
    PRODUCT_ASSETS_BUCKET: str = "product-assets"
    PRODUCT_ASSET_MAX_BYTES: int = 10 * 1024 * 1024
    AVATARS_BUCKET: str = "avatars"
    AVATAR_MAX_BYTES: int = 2 * 1024 * 1024

    # --------------------------------------------------
    # Auth (owned by the backend)
    # --------------------------------------------------

    # HS256 signing secret for session and reset JWTs (also peppers code hashes).
    AUTH_JWT_SECRET: str = ""
    AUTH_SESSION_TTL_SECONDS: int = 604800
    AUTH_COOKIE_SECURE: bool = False
    # True: sign-up needs the emailed code and login refuses unverified accounts.
    # False: sign-up logs the user straight in and login skips the check (use
    # only until email delivery works). No code or email is sent in that mode.
    AUTH_REQUIRE_EMAIL_VERIFICATION: bool = True

    # Fernet key (urlsafe base64, 32 bytes) used to encrypt provider API keys.
    APP_ENCRYPTION_KEY: str = ""

    # --------------------------------------------------
    # Email (SMTP). Empty SMTP_HOST logs codes instead of sending (dev mode).
    # --------------------------------------------------

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True

    # --------------------------------------------------
    # Application
    # --------------------------------------------------

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )

    ADMIN_EMAILS: str = ""

    # --------------------------------------------------
    # Managed AI configuration
    # --------------------------------------------------

    # Render's existing deployment variables. GENERATION_MODEL is for images;
    # the shared provider and API key can also be used for caption generation.
    GENERATION_PROVIDER: str | None = None
    GENERATION_API_KEY: str | None = None
    GENERATION_MODEL: str | None = None

    # القيمة الافتراضية الفارغة مهمة للاختبارات.
    # في التشغيل الحقيقي يجب وضع المفتاح داخل backend/.env.
    OPENAI_API_KEY: str = ""

    IMAGE_PROVIDER: str = "openai"
    TEXT_PROVIDER: str = "openai"

    OPENAI_IMAGE_MODEL: str = "gpt-image-2"
    OPENAI_TEXT_MODEL: str = "gpt-4o-mini"

    # --------------------------------------------------
    # Generation settings
    # --------------------------------------------------

    GENERATION_CREDIT_COST: int = 1
    FREE_TRIAL_DAYS: int = 14
    DAILY_GENERATION_LIMIT: int = 3
    CAPTION_CREDIT_COST: int = 0

    GENERATION_RATE_LIMIT: int = 5
    GENERATION_RATE_WINDOW_SECONDS: int = 60

    GENERATION_LOCK_TTL_SECONDS: int = 180

    ALLOWED_IMAGE_TYPES: str = "image/png,image/jpeg,image/webp"

    # Managed generation compatibility settings. None means use the primary
    # IMAGE_PROVIDER/OPENAI_* settings above.
    MANAGED_PROVIDER: str | None = None
    MANAGED_API_KEY: str | None = None
    MANAGED_MODEL: str | None = None

    # --------------------------------------------------
    # Pydantic Settings
    # --------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"


settings = Settings()


# Fixed, obviously-non-secret value used only outside production so local
# development and tests work without any setup.
_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"


def get_jwt_secret() -> str:
    """Return the JWT signing secret.

    Outside production an empty AUTH_JWT_SECRET falls back to a fixed
    development value. In production an empty secret is a hard error.
    """
    if settings.AUTH_JWT_SECRET:
        return settings.AUTH_JWT_SECRET
    if settings.is_production:
        raise RuntimeError("AUTH_JWT_SECRET must be set when APP_ENV=production")
    return _DEV_JWT_SECRET


def validate_startup_settings() -> None:
    """Called at API startup: refuse to run production without a JWT secret."""
    if settings.AUTH_JWT_SECRET:
        return
    if settings.is_production:
        logger.error("AUTH_JWT_SECRET is empty while APP_ENV=production")
        raise RuntimeError("AUTH_JWT_SECRET must be set when APP_ENV=production")
    logger.warning("AUTH_JWT_SECRET is empty; using an insecure development secret.")
