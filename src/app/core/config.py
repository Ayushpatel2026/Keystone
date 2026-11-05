from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment variables / .env."""

    app_name: str = "Keystone"
    environment: str = "development"
    database_url: str = ""
    secret_key: str = "" # KEYSTONE_SECRET_KEY in .env
    access_token_lifetime_seconds: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KEYSTONE_", extra="ignore")


# cache the settings so that they are only loaded once per process
@lru_cache
def get_settings() -> Settings:
    return Settings()
