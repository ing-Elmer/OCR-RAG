"""Configuración tipada de la aplicación, leída desde variables de entorno."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de OCR-RAG. Falla rápido al arrancar si falta un valor obligatorio."""

    model_config = SettingsConfigDict(
        env_prefix="OCR_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    docs_enabled: bool = True

    db_main_dsn: SecretStr

    jwt_signing_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 15
    refresh_ttl_days: int = 7

    # `NoDecode`: evita que pydantic-settings intente parsear el valor como JSON; la lista
    # se arma a partir de un string separado por comas en `_dividir_origenes_cors`.
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    openai_api_key: SecretStr
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    tesseract_langs: str = "spa+eng"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _dividir_origenes_cors(cls, valor: object) -> object:
        """Permite declarar los orígenes como una lista separada por comas en el `.env`."""
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor


@lru_cache
def get_settings() -> Settings:
    """Instancia única de la configuración, cacheada para todo el proceso."""
    return Settings()
