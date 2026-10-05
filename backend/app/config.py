from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --------------------------------------------------
    # Supabase
    # --------------------------------------------------

    SUPABASE_URL: str = "http://localhost"
    SUPABASE_SECRET_KEY: str = "test-secret-key"
    SUPABASE_ANON_KEY: str = ""

    # --------------------------------------------------
    # Storage
    # --------------------------------------------------

    STORAGE_BUCKET: str = "brand-assets"
    PRODUCT_ASSETS_BUCKET: str = "product-assets"
    PRODUCT_ASSET_MAX_BYTES: int = 10 * 1024 * 1024
    AVATARS_BUCKET: str = "avatars"
    AVATAR_MAX_BYTES: int = 2 * 1024 * 1024

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
    CAPTION_CREDIT_COST: int = 0

    GENERATION_RATE_LIMIT: int = 5
    GENERATION_RATE_WINDOW_SECONDS: int = 60

    GENERATION_LOCK_TTL_SECONDS: int = 180
        # --------------------------------------------------
        # Upload limits
        # --------------------------------------------------
    
    AVATAR_MAX_BYTES: int = 5 * 1024 * 1024
    PRODUCT_ASSET_MAX_BYTES: int = 10 * 1024 * 1024
    
    ALLOWED_IMAGE_TYPES: str = (
            "image/png,image/jpeg,image/webp"
        )
        # --------------------------------------------------
        # Managed generation compatibility settings
        # --------------------------------------------------
    
        # اتركيها فارغة افتراضيًا.
        # القيم الفعلية تأتي من IMAGE_PROVIDER وOPENAI_API_KEY.
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
    


settings = Settings()
