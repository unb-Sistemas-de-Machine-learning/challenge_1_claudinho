"""Configuracao da aplicacao, lida do ambiente (.env em desenvolvimento)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_key: str
    app_env: str = "local"

    # Segredo de assinatura dos JWTs do Supabase Auth. Obrigatorio fora do ambiente
    # local; ver a trava em APP/auth.py:verificar_configuracao.
    supabase_jwt_secret: str | None = None

    # Origens liberadas no CORS fora do ambiente local (dominio do app publicado).
    origens_permitidas: list[str] = []

    # Limite do endpoint /check-claim para imagens (Docs/Production/01, secao 2.1).
    tamanho_maximo_imagem_bytes: int = 5 * 1024 * 1024


@lru_cache
def obter_settings() -> Settings:
    return Settings()
