"""Middleware de logging estruturado — Docs/Production/02, secao 3."""

import hashlib
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import AUTH

TOKEN = AUTH["Authorization"].removeprefix("Bearer ")
ROTA = "/api/v1/check-claim"
CORPO = {"input_type": "text", "text": "ovo faz mal?"}


def test_uma_requisicao_gera_exatamente_um_registro(client, registros_de_log):
    client.post(ROTA, headers=AUTH, json=CORPO)

    assert len(registros_de_log) == 1


def test_o_trace_id_do_log_e_o_mesmo_da_resposta(client, registros_de_log):
    resposta = client.post(ROTA, headers=AUTH, json=CORPO)

    # E o trace_id que costura log, feedback e auditoria: os dois tem que bater.
    assert registros_de_log[0]["trace_id"] == resposta.json()["trace_id"]


def test_o_token_do_usuario_nunca_aparece_no_log(client, registros_de_log):
    import json

    client.post(ROTA, headers=AUTH, json=CORPO)

    registro = registros_de_log[0]
    assert TOKEN not in json.dumps(registro)
    assert registro["user_id_hash"] == "sha256:" + hashlib.sha256(TOKEN.encode()).hexdigest()


def test_requisicao_sem_token_e_registrada_como_anonima(client, registros_de_log):
    client.post(ROTA, json=CORPO)

    assert registros_de_log[0]["user_id_hash"] is None


def test_registro_traz_o_envelope_do_contrato(client, registros_de_log):
    client.post(ROTA, headers=AUTH, json=CORPO)

    registro = registros_de_log[0]
    uuid.UUID(registro["trace_id"])
    assert registro["timestamp"].endswith("Z")
    assert registro["endpoint"] == ROTA
    assert registro["status"] == "success"
    assert registro["error"] is None
    assert isinstance(registro["performance"]["total_latency_ms"], int)
    # Blocos do pipeline de RAG: existem no formato, ainda sem dado para preencher.
    for bloco in ("nlp", "retrieval", "generation", "guardrails"):
        assert bloco in registro


def test_check_claim_preenche_os_blocos_que_ja_tem_dado(client, registros_de_log):
    texto = "agua com limao queima gordura?"

    resposta = client.post(ROTA, headers=AUTH, json={"input_type": "text", "text": texto})

    registro = registros_de_log[0]
    corpo = resposta.json()
    assert registro["input"] == {
        "input_type": "text",
        "raw_length": len(texto),
        "language": "pt-BR",
    }
    assert registro["output"]["verdict"] == corpo["verdict"]
    assert registro["output"]["risk_score"] == corpo["risk_score"]
    assert registro["output"]["sources_count"] == len(corpo["sources"])
    assert registro["performance"]["cache_hit"] is False


def test_o_texto_do_usuario_nao_vai_para_o_log(client, registros_de_log):
    """Secao 3.1: o log guarda formato e tamanho, nao o conteudo."""
    import json

    texto = "tenho gastrite, posso tomar agua com limao?"

    client.post(ROTA, headers=AUTH, json={"input_type": "text", "text": texto})

    assert texto not in json.dumps(registros_de_log[0], ensure_ascii=False)


def test_health_nao_polui_o_log(client, registros_de_log):
    """O provedor bate no /health a cada 30s; logar isso afogaria os registros
    de inferencia de verdade."""
    client.get("/health")

    assert registros_de_log == []


def test_erro_de_validacao_e_registrado_como_erro(client, registros_de_log):
    client.post(ROTA, headers=AUTH, json={"input_type": "text"})

    registro = registros_de_log[0]
    assert registro["status"] == "error"
    assert registro["error"] == "invalid_input"


def test_erro_de_autenticacao_e_registrado_com_o_codigo_do_contrato(client, registros_de_log):
    client.post(
        ROTA, json={"input_type": "text", "text": "x"}, headers={"Authorization": "Bearer "}
    )

    registro = registros_de_log[0]
    assert registro["status"] == "error"
    assert registro["error"] == "unauthorized"


def test_excecao_inesperada_e_registrada_sem_engolir_o_erro(registros_de_log):
    """O middleware observa, nao engole falha: registra e deixa o erro subir."""
    from APP.middleware import LoggingDeInferencia

    app = FastAPI()
    app.add_middleware(LoggingDeInferencia)

    @app.get("/explode")
    async def explode():
        raise RuntimeError("falha proposital")

    with pytest.raises(RuntimeError):
        TestClient(app, raise_server_exceptions=True).get("/explode")

    registro = registros_de_log[0]
    assert registro["status"] == "error"
    assert registro["error"] == "RuntimeError"
