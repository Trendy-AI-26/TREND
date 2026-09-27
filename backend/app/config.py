from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    SUPABASE_ANON_KEY: str = ""
    STORAGE_BUCKET: str = "brand-assets"
    AVATAR_BUCKET: str = "avatars"
    AVATAR_MAX_BYTES: int = 2 * 1024 * 1024
    ADMIN_EMAILS: str = ""
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = (
        "http://localhost:3001,http://127.0.0.1:3001,http://localhost,http://localhost:3000"
    )

    # Managed Generation Settings
    MANAGED_GENERATION_ENABLED: bool = False

    MANAGED_IMAGE_PROVIDER: str = "openai"
    MANAGED_IMAGE_MODEL: str = ""
    MANAGED_IMAGE_API_KEY: str = ""

    MANAGED_TEXT_PROVIDER: str = "openai"
    MANAGED_TEXT_MODEL: str = ""
    MANAGED_TEXT_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore", 
    )


settings = Settings()