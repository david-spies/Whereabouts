# app/core/config.py
from typing import Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Whereabouts"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "PRODUCTION_CHANGE_ME_REQUIRED"

    # Infrastructure Connection Parameters
    DATABASE_URL: str
    CELERY_BROKER_URL: str

    # Vector Space Configurations
    QDRANT_HOST: str = "127.0.0.1"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """
        Dynamically constructs transient RPC backend for task lifecycle tracking.
        """
        return "rpc://"

    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
