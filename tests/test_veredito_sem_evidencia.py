"""Veredito quando os estudos recuperados nao tratam da pergunta.

Achado no app publicado em 06/10: os dois exemplos da tela inicial saiam com o cartao
"Pode confiar" ou "E mito" e, logo abaixo, um texto dizendo que os estudos nao trazem
informacao sobre o tema. A busca tinha devolvido trechos sobre outro assunto, o modelo
percebeu, mas o risk_score que ele mandou junto virava veredito do mesmo jeito.
"""

from datetime import date

import pytest

from APP.config import obter_settings
from APP.model import generator, pipeline
from APP.model.pipeline import executar_pipeline_de_checagem
from APP.schemas import CheckClaimRequest, Fonte
from tests._dubles import PROVEDOR_FALSO

SEM_ESTUDO = "Os estudos disponíveis não trazem informações sobre isso."


def _responder_com(monkeypatch, resposta: dict) -> None:
    monkeypatch.setattr(generator, "gerar_json", lambda *_a, **_k: (resposta, PROVEDOR_FALSO))


def _checar(texto: str):
    return executar_pipeline_de_checagem(
        CheckClaimRequest(input_type="text", text=texto), obter_settings(), 0, "trace"
    )


@pytest.mark.parametrize(
    ("pergunta", "score"),
    [
        ("arroz com feijão é proteína completa mesmo?", 0.1),  # saia "Pode confiar"
        ("pão francês inflama o corpo?", 0.78),  # saia "É mito"
    ],
)
def test_estudos_que_nao_tratam_da_pergunta_viram_sem_evidencia(monkeypatch, pergunta, score):
    _responder_com(
        monkeypatch,
        {"answer": SEM_ESTUDO, "risk_score": score, "evidencia_suficiente": False},
    )

    resposta = _checar(pergunta)

    assert resposta.verdict == "sem_evidencia"
    assert resposta.risk_score == 0.5
    assert resposta.answer == SEM_ESTUDO


def test_padrao_de_consenso_nao_vira_veredito_sem_estudo(monkeypatch):
    """A pergunta casa o padrão de consenso seguro de arroz e feijão. Sem estudo para
    mostrar, o padrão não pode transformar a resposta em "Pode confiar"."""
    _responder_com(
        monkeypatch,
        {"answer": SEM_ESTUDO, "risk_score": 0.1, "evidencia_suficiente": False},
    )

    assert _checar("arroz e feijão juntos formam proteína completa?").verdict == "sem_evidencia"


@pytest.mark.parametrize("negativo", ["false", "False", 0, "0", "no", "não", "nao"])
def test_negativo_escrito_de_outro_jeito_tambem_conta(monkeypatch, negativo):
    """Modelo pequeno às vezes devolve o booleano torto."""
    _responder_com(
        monkeypatch,
        {"answer": SEM_ESTUDO, "risk_score": 0.9, "evidencia_suficiente": negativo},
    )

    assert _checar("pão francês inflama o corpo?").verdict == "sem_evidencia"


def test_sem_evidencia_nao_lista_os_trechos_como_fonte(monkeypatch):
    """Os trechos não tratam da pergunta. Listar como fonte é o veredito com cara de certo
    que o pipeline quer evitar, e o outro caminho de sem_evidencia já devolve sem fonte."""
    _responder_com(
        monkeypatch,
        {"answer": SEM_ESTUDO, "risk_score": 0.1, "evidencia_suficiente": False},
    )

    assert _checar("arroz com feijão é proteína completa mesmo?").sources == []


def test_comparacao_da_tbca_nao_vira_sem_evidencia(monkeypatch):
    """Na TBCA o contexto é tabela, não estudo: o modelo pode dizer que "os estudos não
    tratam" de um dado que a tabela responde direto. Ali vale o score."""
    tabela = Fonte(
        chunk_id="tbca_banana",
        title="Tabela Brasileira de Composição de Alimentos",
        authors="TBCA",
        journal="TBCA",
        published_at=date(2023, 1, 1),
        doi="",
        excerpt="Banana prata: potássio 358 mg em 100 g.",
    )
    monkeypatch.setattr(
        pipeline, "detectar_e_comparar_tbca", lambda _texto: ({"banana": 358}, [tabela])
    )
    _responder_com(
        monkeypatch,
        {
            "answer": "Sim, a banana tem mais potássio [Ref: tbca_banana].",
            "risk_score": 0.1,
            "evidencia_suficiente": False,
        },
    )

    resposta = _checar("banana tem mais potássio que laranja?")

    assert resposta.verdict == "seguro"
    assert [f.chunk_id for f in resposta.sources] == ["tbca_banana"]


@pytest.mark.parametrize("campo", [{"evidencia_suficiente": True}, {}])
def test_com_evidencia_ou_sem_o_campo_o_score_decide(monkeypatch, campo):
    """Sem o campo é o formato das versões de prompt anteriores: nada muda para elas."""
    _responder_com(
        monkeypatch,
        {"answer": "Isso é mito [Ref: chunk_teste_01].", "risk_score": 0.8, **campo},
    )

    assert _checar("pão francês inflama o corpo?").verdict == "desinformacao"
