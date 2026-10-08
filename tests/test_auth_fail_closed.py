"""Regressao dos achados 1, 2 e 8 do review.

1. Esquecer APP_ENV no deploy deixava a API aceitando qualquer token como identidade.
2. A busca da chave publica e HTTP bloqueante: chamada de um caminho async, um atacante
   derrubava a API inteira repetindo tokens com `kid` desconhecido.
8. O mesmo token era validado tres vezes por requisicao.
"""

import asyncio
import time

import pytest
from conftest import AUTH
from pydantic import ValidationError

from APP import auth
from APP.config import Settings
from APP.main import app

ROTA = "/api/v1/check-claim"
CORPO = {"text": "agua com limao emagrece?"}


def _settings(**extra):
    # _env_file=None e a variavel removida do ambiente: so assim da para medir o PADRAO,
    # e nao o valor que o conftest ou o .env do dev definiram.
    base = {"supabase_url": "https://x.supabase.co", "supabase_key": "k", "_env_file": None}
    return Settings(**{**base, **extra})


# ---------- 1. falhar fechado ----------


def test_sem_app_env_o_padrao_e_producao(monkeypatch):
    """Esquecer a variavel no deploy nao pode abrir a API."""
    monkeypatch.delenv("APP_ENV", raising=False)

    assert _settings().app_env == "production"


def test_app_env_escrito_errado_nao_sobe():
    with pytest.raises(ValidationError):
        _settings(app_env="prod")


def test_modo_local_exige_app_env_local(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    token_qualquer = "11111111-1111-1111-1111-111111111111"

    with pytest.raises(auth.ApiError) as erro:
        auth.identidade_do_token(token_qualquer, _settings())

    assert erro.value.codigo == "unauthorized"


# ---------- 8. uma validacao por requisicao ----------


def test_token_e_validado_uma_vez_por_requisicao(client, monkeypatch):
    chamadas = []
    original = auth.identidade_do_token

    def contar(token, settings):
        chamadas.append(token)
        return original(token, settings)

    monkeypatch.setattr(auth, "identidade_do_token", contar)

    client.post(ROTA, headers=AUTH, json=CORPO)

    assert len(chamadas) == 1


# ---------- 2. a validacao nao pode travar o event loop ----------


def test_busca_lenta_da_chave_publica_nao_derruba_a_api(monkeypatch):
    """Com o `kid` desconhecido, o PyJWT vai a rede. Se isso rodar no event loop, o
    /health para de responder junto e a API inteira cai com pouquissimas requisicoes."""
    import httpx

    atraso = 0.4

    def lenta(_token, _settings):
        time.sleep(atraso)  # imita a busca bloqueante do JWKS
        raise auth.ApiError("unauthorized", 401, "token invalido")

    monkeypatch.setattr(auth, "identidade_do_token", lenta)

    async def cenario():
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://t") as cliente:
            ataque = [
                asyncio.create_task(cliente.post(ROTA, headers=AUTH, json=CORPO)) for _ in range(5)
            ]
            await asyncio.sleep(0.05)

            inicio = time.perf_counter()
            saude = await cliente.get("/health")
            tempo_do_health = time.perf_counter() - inicio

            await asyncio.gather(*ataque)
            return saude, tempo_do_health

    saude, tempo_do_health = asyncio.run(cenario())

    assert saude.status_code == 200
    assert tempo_do_health < atraso
