from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Telegram Shop"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    TOKEN_ISSUER: str = "tgshop"

    # Telegram
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_BOT_USERNAME: str = ""
    ADMIN_TELEGRAM_IDS: str = ""
    TELEGRAM_AUTH_MAX_AGE_SECONDS: int = 86400

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://shop:shop@127.0.0.1:5436/shop"

    # CORS
    CORS_ORIGINS: str = "*"

    # Uploads
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # Rate limiting (requests per window per client)
    RATE_LIMIT_MAX: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Abandoned-cart reminders (background task)
    CART_REMINDER_ENABLED: bool = True
    CART_REMINDER_HOURS: float = 24.0
    CART_REMINDER_INTERVAL_SECONDS: int = 3600

    # Online payments
    PAYMENT_GATEWAY: str = "sandbox"

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV.lower() in {"development", "dev", "test"} or self.DEBUG

    @property
    def admin_ids(self) -> list[int]:
        return [
            int(x)
            for x in self.ADMIN_TELEGRAM_IDS.split(",")
            if x.strip().lstrip("-").isdigit()
        ]

    @property
    def cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
