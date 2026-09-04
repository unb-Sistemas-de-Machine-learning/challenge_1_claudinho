"""Acesso ao Supabase (PostgreSQL + pgvector).

O client e criado sob demanda e reaproveitado: importar este modulo nao exige
credenciais, o que mantem o CI e os testes rodando sem segredos.
"""

from functools import lru_cache

from supabase import Client, create_client

from APP.config import obter_settings


@lru_cache
def obter_supabase() -> Client:
    settings = obter_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
