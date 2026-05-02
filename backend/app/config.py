from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440
    UPSTREAM_BASE_URL: str = "http://localhost:2063"
    UPSTREAM_API_KEY: str = "sk-deepseek2api"  # proxy_web_api config api_key for account-pool mode
    ADMIN_EMAIL: str = "admin@transapi.local"
    ADMIN_PASSWORD: str = "changeme"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    APP_NAME: str = "TransAPI Station"
    DEBUG: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
