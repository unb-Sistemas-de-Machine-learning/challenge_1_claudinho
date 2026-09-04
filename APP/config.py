"""Configuracao da aplicacao, lida do ambiente (.env em desenvolvimento)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_key: str
    app_env: str = "local"

    # Limite do endpoint /check-claim para imagens (Docs/Production/01, secao 2.1).
    tamanho_maximo_imagem_bytes: int = 5 * 1024 * 1024


@lru_cache
def obter_settings() -> Settings:
    return Settings()
