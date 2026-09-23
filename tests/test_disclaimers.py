"""Disclaimers homologados e restricao de idade (Docs/Ethics/02 e 03)."""

import re
from datetime import date
from pathlib import Path

import pytest

from APP.model import disclaimers
from APP.routers.profile import _idade
from tests.conftest import AUTH

RAIZ = Path(__file__).resolve().parents[1]
ROTA = "/api/v1/check-claim"


def _documento(nome: str) -> str:
    """Texto do doc sem a marcacao de Markdown (citacao, negrito, quebras de linha)."""
    bruto = (RAIZ / "Docs" / "Ethics" / nome).read_text(encoding="utf-8")
    sem_marcacao = re.sub(r"[>*]", " ", bruto)
    return " ".join(sem_marcacao.split())


# ---------- os textos sao os homologados ----------


@pytest.mark.parametrize(
    ("constante", "documento"),
    [
        ("CURTO", "03_transparencia_e_disclaimers.md"),
        ("EVIDENCIA_LIMITADA", "03_transparencia_e_disclaimers.md"),
        ("GESTANTES_E_LACTANTES", "03_transparencia_e_disclaimers.md"),
        ("CONDICOES_CLINICAS", "03_transparencia_e_disclaimers.md"),
        ("MENOR_DE_IDADE", "02_grupos_de_risco_e_filtros.md"),
    ],
)
def test_texto_e_copia_literal_do_documento_de_etica(constante, documento):
    """Se a Etica mudar a redacao no documento, este teste avisa que o codigo ficou para tras."""
    texto = " ".join(getattr(disclaimers, constante).split())

    assert texto in _documento(documento)


# ---------- quais avisos entram em cada resposta ----------


def test_toda_resposta_comeca_pelo_disclaimer_curto():
    for veredito in ("seguro", "cautela", "desinformacao", "sem_evidencia", "recusa_segura"):
        assert disclaimers.montar_disclaimer(veredito, "ovo faz mal?").startswith(disclaimers.CURTO)


def test_cautela_leva_o_aviso_de_evidencia_limitada():
    assert disclaimers.EVIDENCIA_LIMITADA in disclaimers.montar_disclaimer("cautela", "x")
    assert disclaimers.EVIDENCIA_LIMITADA not in disclaimers.montar_disclaimer("seguro", "x")


@pytest.mark.parametrize(
    "pergunta",
    ["Estou grávida, posso fazer dieta cetogênica?", "Amamentando posso tomar café?"],
)
def test_gestacao_ou_amamentacao_leva_o_aviso_especifico(pergunta):
    assert disclaimers.GESTANTES_E_LACTANTES in disclaimers.montar_disclaimer("seguro", pergunta)


@pytest.mark.parametrize(
    "pergunta",
    ["Sou diabético, posso comer manga?", "Tenho pressão alta, sal rosa é melhor?"],
)
def test_condicao_cronica_leva_o_aviso_de_publicos_especiais(pergunta):
    assert disclaimers.CONDICOES_CLINICAS in disclaimers.montar_disclaimer("seguro", pergunta)


def test_gestante_com_condicao_cronica_nao_repete_o_aviso():
    texto = disclaimers.montar_disclaimer("seguro", "Estou grávida e sou diabética")

    assert disclaimers.GESTANTES_E_LACTANTES in texto
    assert disclaimers.CONDICOES_CLINICAS not in texto


def test_pergunta_comum_leva_so_o_disclaimer_curto():
    assert disclaimers.montar_disclaimer("seguro", "Água com limão emagrece?") == disclaimers.CURTO


# ---------- menor de idade ----------


@pytest.mark.parametrize(
    "pergunta",
    [
        "tenho 15 anos, posso tomar whey?",
        "Tenho quinze anos e quero emagrecer",
        "fiz 17 anos semana passada, jejum faz mal?",
        "sou menor de idade, posso usar?",
    ],
)
def test_detecta_menor_de_idade_na_pergunta(pergunta):
    assert disclaimers.e_menor_de_idade(pergunta)


@pytest.mark.parametrize(
    "pergunta",
    [
        "tenho 18 anos, posso tomar whey?",
        "tenho 25 anos e quero emagrecer",
        "meu filho tem 15 anos, pode tomar whey?",  # quem pergunta e o responsavel
        "tenho 15 anos de diabetes, posso comer manga?",  # duracao, nao idade
        "como arroz e feijão há 15 anos",
    ],
)
def test_nao_confunde_adulto_com_menor(pergunta):
    assert not disclaimers.e_menor_de_idade(pergunta)


def test_menor_de_idade_recebe_recusa_sem_busca_nem_llm(client, base_de_teste):
    resposta = client.post(ROTA, headers=AUTH, json={"text": "tenho 15 anos, whey faz mal?"})

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["verdict"] == "recusa_segura"
    assert corpo["answer"] == disclaimers.MENOR_DE_IDADE
    assert corpo["sources"] == []
    assert base_de_teste.chamadas_rpc == 0


def test_rota_devolve_o_disclaimer_homologado(client):
    resposta = client.post(ROTA, headers=AUTH, json={"text": "Água com limão emagrece?"})

    assert resposta.json()["disclaimer"].startswith(disclaimers.CURTO)


# ---------- idade pelo perfil ----------


@pytest.mark.parametrize(
    ("nascimento", "hoje", "idade"),
    [
        (date(2008, 9, 21), date(2026, 9, 21), 18),  # aniversario hoje
        (date(2008, 9, 22), date(2026, 9, 21), 17),  # faz 18 amanha
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # nascido em 29/02
    ],
)
def test_calculo_de_idade(nascimento, hoje, idade):
    assert _idade(nascimento, hoje) == idade


def _anos_atras(anos: int, dias_a_mais: int = 0) -> str:
    hoje = date.today()
    try:
        data = hoje.replace(year=hoje.year - anos)
    except ValueError:  # 29/02 em ano nao bissexto
        data = hoje.replace(year=hoje.year - anos, day=28)
    return date.fromordinal(data.toordinal() + dias_a_mais).isoformat()


def test_perfil_de_menor_de_idade_e_recusado(client):
    resposta = client.put(
        "/api/v1/profile", headers=AUTH, json={"birth_date": _anos_atras(18, dias_a_mais=1)}
    )

    assert resposta.status_code == 403
    assert resposta.json()["error"] == "age_restricted"
    assert resposta.json()["detail"] == disclaimers.MENOR_DE_IDADE


def test_perfil_de_quem_acabou_de_fazer_18_e_aceito(client):
    resposta = client.put("/api/v1/profile", headers=AUTH, json={"birth_date": _anos_atras(18)})

    assert resposta.status_code == 200
