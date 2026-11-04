from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment variables / .env."""

    app_name: str = "Keystone"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="KEYSTONE_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
