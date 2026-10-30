from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EV Platform API"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./ev_platform.db"
    redis_url: str = "redis://localhost:6379"

    # No built-in signing key: the operator must provide SECRET_KEY.
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Login is disabled until an administrator provides a password hash.
    admin_username: str = "admin"
    admin_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    admin_password_hash: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
