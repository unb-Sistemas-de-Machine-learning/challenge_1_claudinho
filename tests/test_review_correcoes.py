"""Regressao dos achados 3 a 7 e 10 do review.

Cada teste reproduz o cenario descrito no review antes de verificar a correcao.
"""

import pytest
from conftest import AUTH

from APP.model import retriever
from APP.model.claim_extractor import checar_recusa_segura
from APP.model.generator import _definir_nivel_risco
from APP.verdict import LIMIAR_DESINFORMACAO, LIMIAR_SEGURO, classificar_veredito

ROTA = "/api/v1/check-claim"


# ---------- 3. print e link nao sao lidos ----------


@pytest.mark.parametrize(
    "corpo",
    [
        {"input_type": "image", "image_base64": "aGVsbG8="},
        {"input_type": "url", "url": "https://instagram.com/reel/C9x2pao"},
    ],
    ids=["print", "link"],
)
def test_entrada_que_a_api_nao_le_e_recusada(client, base_de_teste, corpo):
    """Antes, toda imagem virava a mesma frase fixa: o usuario recebia veredito, score e
    DOI sobre um assunto sem relacao com o print."""
    resposta = client.post(ROTA, headers=AUTH, json=corpo)

    assert resposta.status_code == 422
    assert resposta.json()["error"] == "input_nao_suportado"
    assert base_de_teste.chamadas_rpc == 0


def test_dois_prints_diferentes_nao_recebem_a_mesma_resposta(client):
    primeira = client.post(ROTA, headers=AUTH, json={"input_type": "image", "image_base64": "YQ=="})
    segunda = client.post(ROTA, headers=AUTH, json={"input_type": "image", "image_base64": "Yg=="})

    assert primeira.status_code == segunda.status_code == 422
    assert "sources" not in primeira.json()


# ---------- 4. substring nos padroes de risco ----------


@pytest.mark.parametrize(
    "pergunta",
    ["bolacha cream cracker engorda?", "é verdade que açúcar é veneno branco?"],
    ids=["cream cracker", "veneno branco"],
)
def test_palavra_dentro_de_outra_nao_aciona_recusa(pergunta):
    """ "crack" casava dentro de "cream cracker" e "veneno" dentro de "veneno branco",
    que e giria para acucar."""
    recusou, _ = checar_recusa_segura(pergunta)

    assert not recusou


@pytest.mark.parametrize("pergunta", ["cocaina emagrece?", "tomar veneno de rato desintoxica?"])
def test_substancia_toxica_continua_barrada(pergunta):
    recusou, _ = checar_recusa_segura(pergunta)

    assert recusou


# ---------- 5. substring na deteccao de alimentos ----------


def test_alimento_dentro_de_outra_palavra_nao_desvia_para_a_tbca(monkeypatch):
    """ "alho" casava em "trabalho" e "pao" no fim de uma URL: a pergunta ia para a
    comparacao de calorias sem passar pelos estudos."""
    consultas = []
    monkeypatch.setattr(retriever, "buscar_alimento_tbca", lambda termo: consultas.append(termo))

    for frase in ("da muito trabalho fazer arroz integral?", "https://instagram.com/reel/C9x2pao"):
        retriever.detectar_e_comparar_tbca(frase)

    assert "alho" not in consultas
    assert "pao" not in consultas


def test_comparacao_exige_termo_nutricional(monkeypatch):
    """Citar dois alimentos nao quer dizer que a pergunta e sobre composicao."""
    consultas = []
    monkeypatch.setattr(retriever, "buscar_alimento_tbca", lambda termo: consultas.append(termo))

    retriever.detectar_e_comparar_tbca("posso comer arroz e feijao todo dia?")

    assert consultas == []


# ---------- 6 e 7. casos que viravam 500 ----------


def test_chunk_com_conteudo_nulo_nao_derruba_a_requisicao(client, base_de_teste):
    """Coluna NULL no banco: c.get("conteudo", "") devolvia None e None.strip() estourava
    AttributeError fora do try, virando 500 em vez do fallback."""
    base_de_teste.chunks = [
        {"chunk_id": "c1", "article_id": "a1", "similaridade": 0.9, "conteudo": None}
    ]

    resposta = client.post(ROTA, headers=AUTH, json={"text": "ovo faz mal?"})

    assert resposta.status_code == 200


def test_provedor_com_content_nulo_cai_no_fallback(client, base_de_teste, monkeypatch):
    """Gemini responde 200 com content null quando o filtro de seguranca recusa."""
    from APP.model import llm

    def sem_conteudo(*_args, **_kwargs):
        raise llm.GeracaoIndisponivel("provedor devolveu resposta sem conteudo de texto")

    monkeypatch.setattr("APP.model.generator.gerar_json", sem_conteudo)

    resposta = client.post(ROTA, headers=AUTH, json={"text": "agua com limao emagrece?"})

    assert resposta.status_code == 200
    assert resposta.json()["model_version"].startswith("fallback-local")


# ---------- 10. limiares com um dono so ----------


@pytest.mark.parametrize(
    ("score", "veredito", "nivel"),
    [(0.10, "seguro", "baixo"), (0.50, "cautela", "medio"), (0.90, "desinformacao", "alto")],
)
def test_nivel_de_risco_acompanha_o_veredito(score, veredito, nivel):
    assert classificar_veredito(score) == veredito
    assert _definir_nivel_risco(score) == nivel


def test_mudar_o_limiar_no_verdict_move_os_dois(monkeypatch):
    """Os limiares tinham copia no generator: mudar a calibracao no verdict.py fazia a
    mesma resposta sair com verdict "cautela" e risk_level "alto"."""
    assert _definir_nivel_risco(LIMIAR_SEGURO) == "medio"
    assert _definir_nivel_risco(LIMIAR_SEGURO - 0.01) == "baixo"
    assert _definir_nivel_risco(LIMIAR_DESINFORMACAO) == "medio"
    assert _definir_nivel_risco(LIMIAR_DESINFORMACAO + 0.01) == "alto"
