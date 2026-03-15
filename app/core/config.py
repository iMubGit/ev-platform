from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "EV Platform API"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./ev_platform.db"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"


settings = Settings()