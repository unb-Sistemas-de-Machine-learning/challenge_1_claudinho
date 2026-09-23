"""Regressao dos consertos de producao do /check-claim (review do PR #13).

- O pipeline e sincrono e pode esperar a LLM por ate 25 s. Rodando direto na rota
  async, ele travava o event loop e derrubava ate o /health.
- O `latency_ms` da resposta era medido antes do pipeline rodar e saia perto de zero.

Os testes substituem o pipeline por uma versao lenta (`time.sleep`, que bloqueia de
verdade, como o httpx sincrono faz) para exercitar exatamente esse cenario.
"""

import asyncio
import time

import httpx

from APP.main import app
from APP.model import pipeline as modulo_pipeline
from APP.routers import check_claim as modulo_rota
from tests.conftest import AUTH

ATRASO_S = 0.5
CORPO = {"text": "agua com limao emagrece?"}


def _pipeline_lento(monkeypatch):
    original = modulo_pipeline.executar_pipeline_de_checagem

    def lento(*args, **kwargs):
        time.sleep(ATRASO_S)
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo_rota, "executar_pipeline_de_checagem", lento)


def test_health_responde_enquanto_o_pipeline_espera_a_llm(monkeypatch):
    _pipeline_lento(monkeypatch)

    async def cenario():
        transporte = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://t") as cliente:
            inicio = time.perf_counter()
            lenta = asyncio.create_task(
                cliente.post("/api/v1/check-claim", headers=AUTH, json=CORPO)
            )
            await asyncio.sleep(0.05)  # garante que a checagem ja esta no pipeline

            saude = await cliente.get("/health")
            tempo_do_health = time.perf_counter() - inicio

            resposta_lenta = await lenta
            return saude, tempo_do_health, resposta_lenta

    saude, tempo_do_health, resposta_lenta = asyncio.run(cenario())

    assert saude.status_code == 200
    assert resposta_lenta.status_code == 200
    # Se o loop estivesse travado, o /health so voltaria depois do pipeline terminar.
    assert tempo_do_health < ATRASO_S


def test_latencia_da_resposta_inclui_o_tempo_do_pipeline(client, monkeypatch):
    _pipeline_lento(monkeypatch)

    resposta = client.post("/api/v1/check-claim", headers=AUTH, json=CORPO)

    assert resposta.status_code == 200
    assert resposta.json()["latency_ms"] >= ATRASO_S * 1000
