"""Configuracao da aplicacao, lida do ambiente (.env em desenvolvimento)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_key: str
    # Padrao "production" DE PROPOSITO: esquecer a variavel no deploy tem que falhar
    # FECHADO. Com o padrao "local", a API aceitaria qualquer token como identidade.
    # O tipo Literal faz o pydantic recusar um valor escrito errado ("prod", "Local")
    # na subida, em vez de cair silenciosamente fora do modo local.
    app_env: Literal["local", "staging", "production"] = "production"

    # Segredo de assinatura dos JWTs do Supabase Auth (Project Settings > API > JWT Secret).
    # Obrigatorio fora do ambiente local; ver a trava em APP/auth.py:verificar_configuracao.
    supabase_jwt_secret: str | None = None

    # Origens liberadas no CORS fora do ambiente local (dominio do app publicado).
    origens_permitidas: list[str] = []

    # Limite do endpoint /check-claim para imagens (Docs/Production/01, secao 2.1).
    tamanho_maximo_imagem_bytes: int = 5 * 1024 * 1024

    # LLM proprio (Ollama no Hugging Face Spaces), tentado antes dos externos.
    # Ver APP/model/llm.py e deploy/ollama-space/README.md.
    llm_base_url: str | None = None
    llm_modelo: str = "qwen2.5:3b"
    # Token do Hugging Face quando o Space e privado.
    llm_api_key: str | None = None
    # Modelo de 3B em CPU gratuita leva de 20 a 60 s por resposta.
    llm_timeout_s: float = 90.0

    # Provedores externos de reserva, na ordem em que sao tentados.
    gemini_api_key: str | None = None
    gemini_modelo: str = "gemini-3.5-flash-lite"
    openai_api_key: str | None = None
    openai_modelo: str = "gpt-4o-mini"
    # Servico remoto de embeddings. Com ele configurado, a API nao carrega o modelo e nao
    # precisa do torch: cabe em plataforma serverless (Vercel) e no Render gratuito. Sem
    # ele, usa o modelo local (so desenvolvimento). Ver APP/model/embeddings.py.
    embeddings_url: str | None = None
    # "hf-inference": API de inferencia do Hugging Face (nao precisa de Space; e o padrao).
    # "space": servico proprio de deploy/embeddings-space (exige conta PRO para criar).
    embeddings_provedor: Literal["hf-inference", "space"] = "hf-inference"
    # Token do Hugging Face. Para "hf-inference", precisa da permissao
    # "Make calls to Inference Providers".
    embeddings_token: str | None = None
    embeddings_timeout_s: float = 20.0


@lru_cache
def obter_settings() -> Settings:
    return Settings()
