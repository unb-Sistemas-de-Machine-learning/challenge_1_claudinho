import json

import httpx
import pytest

from APP.config import Settings
from APP.model.llm import (
    GEMINI_BASE_URL,
    GeracaoIndisponivel,
    Provedor,
    gerar_json,
    provedores_configurados,
)

PROPRIO = Provedor("ollama", "https://proprio.hf.space/v1", "qwen2.5:3b", "hf_token", 90.0, True)
EXTERNO = Provedor("gemini", "https://externo.test/v1", "gemini-x", "chave-externa")


def _resposta_de_chat(conteudo: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": conteudo}}]})


def _transporte(respostas_por_host: dict[str, object], chamados: list[httpx.Request]):
    """Responde conforme o host. Uma excecao na tabela e levantada, simulando a rede."""

    def responder(requisicao: httpx.Request) -> httpx.Response:
        chamados.append(requisicao)
        resposta = respostas_por_host[requisicao.url.host]
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    return httpx.MockTransport(responder)


def test_usa_o_primeiro_provedor_quando_ele_responde():
    chamados: list[httpx.Request] = []
    transporte = _transporte(
        {"proprio.hf.space": _resposta_de_chat('{"answer": "ok", "risk_score": 0.2}')}, chamados
    )

    objeto, provedor = gerar_json("sistema", "usuario", [PROPRIO, EXTERNO], transporte=transporte)

    assert objeto == {"answer": "ok", "risk_score": 0.2}
    assert provedor.versao == "ollama/qwen2.5:3b"
    assert len(chamados) == 1


def test_manda_o_formato_da_openai_com_modo_json_e_token():
    chamados: list[httpx.Request] = []
    transporte = _transporte({"proprio.hf.space": _resposta_de_chat("{}")}, chamados)

    gerar_json("sistema", "usuario", [PROPRIO], transporte=transporte)

    requisicao = chamados[0]
    assert str(requisicao.url) == "https://proprio.hf.space/v1/chat/completions"
    assert requisicao.headers["authorization"] == "Bearer hf_token"
    corpo = json.loads(requisicao.content)
    assert corpo["model"] == "qwen2.5:3b"
    assert corpo["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]


@pytest.mark.parametrize(
    "falha",
    [
        httpx.Response(503),
        httpx.ReadTimeout("demorou"),
        httpx.ConnectError("Space dormindo"),
        _resposta_de_chat("isto nao e json"),
        _resposta_de_chat("[1, 2]"),
        httpx.Response(200, json={"sem": "choices"}),
    ],
    ids=["http-503", "timeout", "conexao", "json-quebrado", "json-nao-objeto", "formato-errado"],
)
def test_cai_para_o_proximo_provedor_quando_o_primeiro_falha(falha):
    chamados: list[httpx.Request] = []
    transporte = _transporte(
        {
            "proprio.hf.space": falha,
            "externo.test": _resposta_de_chat('{"answer": "reserva"}'),
        },
        chamados,
    )

    objeto, provedor = gerar_json("sistema", "usuario", [PROPRIO, EXTERNO], transporte=transporte)

    assert objeto == {"answer": "reserva"}
    assert provedor.nome == "gemini"


def test_aceita_json_dentro_de_cerca_de_codigo():
    chamados: list[httpx.Request] = []
    conteudo = '```json\n{"answer": "ok"}\n```'
    transporte = _transporte({"proprio.hf.space": _resposta_de_chat(conteudo)}, chamados)

    objeto, _ = gerar_json("sistema", "usuario", [PROPRIO], transporte=transporte)

    assert objeto == {"answer": "ok"}


def test_dado_sensivel_nunca_vai_para_provedor_externo():
    chamados: list[httpx.Request] = []
    transporte = _transporte(
        {
            "proprio.hf.space": httpx.Response(500),
            "externo.test": _resposta_de_chat('{"answer": "vazou"}'),
        },
        chamados,
    )

    with pytest.raises(GeracaoIndisponivel):
        gerar_json(
            "sistema", "usuario", [PROPRIO, EXTERNO], dados_sensiveis=True, transporte=transporte
        )

    assert [r.url.host for r in chamados] == ["proprio.hf.space"]


def test_sem_provedor_elegivel_levanta_erro():
    with pytest.raises(GeracaoIndisponivel):
        gerar_json("sistema", "usuario", [])


def test_todos_falhando_levanta_erro():
    chamados: list[httpx.Request] = []
    transporte = _transporte(
        {"proprio.hf.space": httpx.Response(500), "externo.test": httpx.Response(429)}, chamados
    )

    with pytest.raises(GeracaoIndisponivel):
        gerar_json("sistema", "usuario", [PROPRIO, EXTERNO], transporte=transporte)

    assert len(chamados) == 2


def _settings(**valores) -> Settings:
    return Settings(supabase_url="https://x.supabase.co", supabase_key="k", **valores)


def test_cadeia_poe_o_modelo_proprio_antes_dos_externos():
    provedores = provedores_configurados(
        _settings(
            llm_base_url="https://proprio.hf.space/v1",
            llm_api_key="hf_token",
            gemini_api_key="chave-gemini",
            openai_api_key="chave-openai",
        )
    )

    assert [p.nome for p in provedores] == ["ollama", "gemini", "openai"]
    assert [p.aceita_dados_sensiveis for p in provedores] == [True, False, False]
    assert provedores[1].base_url == GEMINI_BASE_URL


def test_cadeia_so_tem_o_que_foi_configurado():
    assert provedores_configurados(_settings()) == []
    assert [p.nome for p in provedores_configurados(_settings(gemini_api_key="k"))] == ["gemini"]


def test_gerador_usa_o_fallback_local_quando_nenhum_provedor_responde(monkeypatch):
    """Antes devolvia 503. Decisao do grupo: sem LLM, o classificador decide o veredito
    e a resposta e montada com os trechos recuperados (APP/model/resposta_local.py)."""
    from APP.model import generator
    from APP.model.resposta_local import MODEL_VERSION
    from APP.schemas import Fonte

    def falhar(*_args, **_kwargs):
        raise GeracaoIndisponivel("todos os provedores falharam")

    monkeypatch.setattr(generator, "gerar_json", falhar)
    fonte = Fonte(
        chunk_id="c1",
        title="t",
        authors="a",
        journal="j",
        published_at="2021-01-01",
        doi="d",
        excerpt="e",
    )

    resposta, _score, veredito, modelo, _versao = generator.gerar_resposta_grounded(
        "alegacao",
        [fonte],
        [{"chunk_id": "c1", "titulo": "t", "conteudo": "e"}],
        _settings(llm_base_url="https://proprio.hf.space/v1"),
    )

    assert modelo == MODEL_VERSION
    assert veredito in {"seguro", "cautela", "desinformacao"}
    assert resposta.strip()
