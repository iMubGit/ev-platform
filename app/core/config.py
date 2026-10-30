from typing import Literal
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
    # Only this explicitly supported signing algorithm is accepted.
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 30

    # Login protection: fixed 15-minute window by default.
    login_rate_limit_per_identity: int = Field(default=5, ge=1)
    login_rate_limit_per_ip: int = Field(default=20, ge=1)
    login_rate_limit_window_seconds: int = Field(default=900, ge=1)

    # Login is disabled until an administrator provides a password hash.
    admin_username: str = "admin"
    admin_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    admin_password_hash: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
