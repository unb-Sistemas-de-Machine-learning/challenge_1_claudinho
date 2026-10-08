"""Cliente de embeddings (APP/model/embeddings.py).

O modo remoto existe para a API ficar leve na Vercel e no Render gratuito. Estes testes
garantem que ela continua leve, que o cliente fala o formato de cada provedor
(API do Hugging Face e Space proprio), e que falha do provedor vira 503, nao "sem evidencia".
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from APP.config import Settings
from APP.model import embeddings, retriever
from tests.conftest import AUTH

RAIZ = Path(__file__).resolve().parents[1]
URL_HF = (
    "https://router.huggingface.co/hf-inference/models/"
    "intfloat/multilingual-e5-base/pipeline/feature-extraction"
)
URL_SPACE = "https://usuario-embeddings.hf.space"


def _settings(provedor="hf-inference", **extra):
    base = {
        "supabase_url": "https://x.supabase.co",
        "supabase_key": "x",
        "embeddings_url": URL_HF if provedor == "hf-inference" else URL_SPACE,
        "embeddings_provedor": provedor,
    }
    return Settings(**{**base, **extra})


@pytest.fixture
def provedor_falso(monkeypatch):
    """Provedor remoto falso: registra o pedido e responde o que o teste mandar."""
    estado = {"pedidos": [], "resposta": [0.1] * 768}

    def responder(pedido: httpx.Request) -> httpx.Response:
        estado["pedidos"].append(
            {"url": str(pedido.url), "headers": pedido.headers, "corpo": json.loads(pedido.content)}
        )
        resposta = estado["resposta"]
        if isinstance(resposta, httpx.Response):
            return resposta
        return httpx.Response(200, json=resposta)

    original = httpx.Client
    transporte = httpx.MockTransport(responder)
    monkeypatch.setattr(
        embeddings.httpx, "Client", lambda **kw: original(transport=transporte, **kw)
    )
    return estado


def _usar(monkeypatch, **kwargs):
    monkeypatch.setattr(embeddings, "obter_settings", lambda: _settings(**kwargs))


def test_importar_o_cliente_nao_puxa_o_torch():
    """E o motivo de existir o modo remoto: sem isto a API nao cabe na Vercel (500 MB)."""
    codigo = (
        "import sys, APP.model.embeddings, APP.model.retriever;"
        "print('torch' in sys.modules or 'sentence_transformers' in sys.modules)"
    )
    # Herda o ambiente do sistema: no Windows, sem SYSTEMROOT o Python nem inicializa a
    # rede (WinError 10106). So as credenciais obrigatorias sao sobrescritas.
    ambiente = {**os.environ, "SUPABASE_URL": "x", "SUPABASE_KEY": "x"}
    saida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, env=ambiente
    )

    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "False"


# ---------- API de inferencia do Hugging Face (padrao) ----------


def test_hf_inference_manda_o_formato_da_api(monkeypatch, provedor_falso):
    _usar(monkeypatch, embeddings_token="hf_x")

    vetor = embeddings.gerar_embedding_consulta("agua com limao emagrece?")

    pedido = provedor_falso["pedidos"][0]
    assert len(vetor) == 768
    assert pedido["url"] == URL_HF
    assert pedido["corpo"] == {"inputs": "query: agua com limao emagrece?", "normalize": True}
    assert pedido["headers"]["authorization"] == "Bearer hf_x"


def test_hf_inference_aceita_resposta_aninhada(monkeypatch, provedor_falso):
    """Algumas versoes da API devolvem [[...]] em vez de [...] para um unico texto."""
    _usar(monkeypatch)
    provedor_falso["resposta"] = [[0.2] * 768]

    assert embeddings.gerar_embedding_consulta("ovo") == [0.2] * 768


def test_cota_esgotada_aparece_no_motivo_do_erro(monkeypatch, provedor_falso):
    """HTTP 402 = cota mensal gratuita do Hugging Face acabou. O log precisa dizer isso."""
    _usar(monkeypatch)
    provedor_falso["resposta"] = httpx.Response(402)

    with pytest.raises(embeddings.EmbeddingsIndisponiveis, match="HTTP 402"):
        embeddings.gerar_embedding_consulta("ovo")


# ---------- Space proprio ----------


def test_space_manda_o_formato_do_servico(monkeypatch, provedor_falso):
    _usar(monkeypatch, provedor="space")
    provedor_falso["resposta"] = {"vetores": [[0.1] * 768]}

    embeddings.gerar_embedding_consulta("ovo")

    pedido = provedor_falso["pedidos"][0]
    assert pedido["url"] == f"{URL_SPACE}/embed"
    assert pedido["corpo"] == {"textos": ["query: ovo"]}


# ---------- regras comuns aos dois provedores ----------


@pytest.mark.parametrize("provedor", ["hf-inference", "space"])
def test_prefixo_nao_e_duplicado(monkeypatch, provedor_falso, provedor):
    _usar(monkeypatch, provedor=provedor)
    if provedor == "space":
        provedor_falso["resposta"] = {"vetores": [[0.1] * 768]}

    embeddings.gerar_embedding_consulta("query: ja formatado")

    corpo = provedor_falso["pedidos"][0]["corpo"]
    assert (corpo.get("inputs") or corpo["textos"][0]) == "query: ja formatado"


@pytest.mark.parametrize("provedor", ["hf-inference", "space"])
def test_vetor_de_outra_dimensao_e_recusado(monkeypatch, provedor_falso, provedor):
    """Outro modelo (ex.: e5-large, 1024) quebraria a busca no pgvector."""
    _usar(monkeypatch, provedor=provedor)
    provedor_falso["resposta"] = (
        [0.1] * 1024 if provedor == "hf-inference" else {"vetores": [[0.1] * 1024]}
    )

    with pytest.raises(embeddings.EmbeddingsIndisponiveis, match="1024"):
        embeddings.gerar_embedding_consulta("ovo")


@pytest.mark.parametrize("provedor", ["hf-inference", "space"])
@pytest.mark.parametrize(
    "falha",
    [httpx.Response(503), httpx.Response(200, json={"outra": "coisa"})],
    ids=["fora-do-ar", "resposta-sem-vetor"],
)
def test_falha_do_provedor_vira_erro_de_embeddings(monkeypatch, provedor_falso, provedor, falha):
    _usar(monkeypatch, provedor=provedor)
    provedor_falso["resposta"] = falha

    with pytest.raises(embeddings.EmbeddingsIndisponiveis):
        embeddings.gerar_embedding_consulta("ovo")


def test_provedor_fora_do_ar_responde_503_e_nao_sem_evidencia(client, monkeypatch):
    """Provedor fora do ar nao e 'a base nao tem estudos': isso seria uma resposta falsa."""

    def fora_do_ar(_texto):
        raise embeddings.EmbeddingsIndisponiveis("HTTP 402")

    monkeypatch.setattr(retriever, "gerar_embedding_consulta", fora_do_ar)

    resposta = client.post("/api/v1/check-claim", headers=AUTH, json={"text": "ovo faz mal?"})

    assert resposta.status_code == 503
    assert resposta.json()["error"] == "upstream_unavailable"


def test_motivo_da_falha_vai_para_o_log(client, monkeypatch, registros_de_log):
    def cota_esgotada(_texto):
        raise embeddings.EmbeddingsIndisponiveis("HTTP 402")

    monkeypatch.setattr(retriever, "gerar_embedding_consulta", cota_esgotada)

    client.post("/api/v1/check-claim", headers=AUTH, json={"text": "ovo faz mal?"})

    assert registros_de_log[-1]["retrieval"]["detalhe"] == "HTTP 402"


# ---------- contrato entre o cliente e o servico do Space ----------


class _ModeloFalso:
    def encode(self, textos, normalize_embeddings=True):
        assert normalize_embeddings  # a base foi indexada com vetores normalizados
        return _Lista([[0.5] * 768 for _ in textos])


class _Lista(list):
    def tolist(self):
        return list(self)


def _carregar_servico_do_space():
    caminho = RAIZ / "deploy" / "embeddings-space" / "app.py"
    especificacao = importlib.util.spec_from_file_location("servico_embeddings", caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_cliente_e_servico_do_space_falam_o_mesmo_contrato(monkeypatch):
    servico = _carregar_servico_do_space()
    servico._estado["modelo"] = _ModeloFalso()  # o torch nao e carregado no teste

    with TestClient(servico.app) as cliente_do_space:
        monkeypatch.setattr(embeddings.httpx, "Client", lambda **_kw: cliente_do_space)
        _usar(monkeypatch, provedor="space")

        vetor = embeddings.gerar_embedding_consulta("agua com limao emagrece?")
        saude = cliente_do_space.get("/health").json()

    assert vetor == [0.5] * 768
    assert saude == {"status": "ok", "modelo": "intfloat/multilingual-e5-base", "carregado": True}


def test_matriz_token_a_token_e_recusada(monkeypatch, provedor_falso):
    """Achado 12 do review: cada linha da matriz de tokens tambem tem 768 posicoes, entao
    pegar a linha 0 passaria na checagem de dimensao e a busca usaria o embedding do
    primeiro token em vez do da frase, sem erro e sem log."""
    _usar(monkeypatch)
    provedor_falso["resposta"] = [[0.1] * 768, [0.2] * 768, [0.3] * 768]

    with pytest.raises(embeddings.EmbeddingsIndisponiveis, match="matriz por token"):
        embeddings.gerar_embedding_consulta("ovo")
