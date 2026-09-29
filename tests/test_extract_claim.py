"""Extracao rapida da alegacao (issue #26).

A tela de carregamento precisa mostrar "Entendi assim: ..." ANTES de a resposta chegar.
Por isso este endpoint nao pode depender de LLM, embedding nem banco.
"""

import pytest
from conftest import AUTH

ROTA = "/api/v1/extract-claim"


def test_devolve_a_pergunta_reformulada(client):
    resposta = client.post(ROTA, headers=AUTH, json={"text": "agua com limao emagrece???"})

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["canonical_claim"]
    assert corpo["safe_refusal"] is False


def test_nao_toca_no_banco_nem_na_llm(client, base_de_teste, monkeypatch):
    """E o que permite responder em milissegundos, durante o carregamento."""

    def nao_deveria(*_args, **_kwargs):
        raise AssertionError("o endpoint de extracao nao pode chamar a geracao")

    monkeypatch.setattr("APP.model.generator.gerar_resposta_grounded", nao_deveria)

    client.post(ROTA, headers=AUTH, json={"text": "detox funciona?"})

    assert base_de_teste.chamadas_rpc == 0


def test_avisa_quando_a_checagem_vai_terminar_em_recusa(client):
    """A tela nao pode prometer "procurando nos estudos" para uma pergunta que vai receber
    resposta de cuidado."""
    resposta = client.post(
        ROTA, headers=AUTH, json={"text": "Como vomitar depois de comer para nao engordar?"}
    )

    assert resposta.json()["safe_refusal"] is True


def test_nao_registra_o_texto_da_duvida_no_log(client, registros_de_log):
    duvida = "tenho diabetes tipo 1, posso fazer jejum?"

    client.post(ROTA, headers=AUTH, json={"text": duvida})

    registro = registros_de_log[-1]
    assert "diabetes" not in str(registro)
    assert registro["input"]["raw_length"] == len(duvida)


@pytest.mark.parametrize("corpo", [{}, {"text": ""}, {"text": "x" * 2001}])
def test_recusa_entrada_invalida(client, corpo):
    assert client.post(ROTA, headers=AUTH, json=corpo).status_code == 400


def test_exige_autenticacao(client):
    assert client.post(ROTA, json={"text": "ovo faz mal?"}).status_code == 401


def test_nao_gasta_a_cota_de_checagens(client):
    """Limite proprio (escrita): senao, cada checagem custaria duas da cota de 10/min."""
    for _ in range(11):
        client.post(ROTA, headers=AUTH, json={"text": "ovo faz mal?"})

    checagem = client.post(
        "/api/v1/check-claim", headers=AUTH, json={"text": "agua com limao emagrece?"}
    )

    assert checagem.status_code == 200
