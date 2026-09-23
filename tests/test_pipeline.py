"""Pipeline de checagem, caminho por caminho (issue #11).

Cada teste controla o que o banco (fixture `base_de_teste`, do conftest) e a LLM
(`llm_falsa`, abaixo) devolvem, e verifica o que o pipeline faz com isso. Nada aqui
acessa rede nem carrega modelo.
"""

import pytest

from APP.config import obter_settings
from APP.model import generator
from APP.model.llm import GeracaoIndisponivel
from APP.model.pipeline import executar_pipeline_de_checagem
from APP.model.resposta_local import MODEL_VERSION as MODELO_FALLBACK
from APP.schemas import CheckClaimRequest
from tests._dubles import CHUNK_PADRAO, PROVEDOR_FALSO

TRACE = "00000000-0000-0000-0000-000000000000"


class _LLMFalsa:
    """Substitui o cliente de LLM: devolve uma resposta fixa e conta as chamadas."""

    def __init__(self):
        self.resposta: dict | Exception = {
            "answer": f"Resposta informativa\nTexto do modelo [Ref: {CHUNK_PADRAO['chunk_id']}]",
            "risk_score": 0.2,
        }
        self.chamadas = 0

    def __call__(self, *_args, **_kwargs):
        self.chamadas += 1
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta, PROVEDOR_FALSO


@pytest.fixture
def llm_falsa(monkeypatch):
    falsa = _LLMFalsa()
    monkeypatch.setattr(generator, "gerar_json", falsa)
    return falsa


def _checar(texto: str):
    return executar_pipeline_de_checagem(
        CheckClaimRequest(input_type="text", text=texto), obter_settings(), 0, TRACE
    )


# ---------- guardrail ----------


def test_guardrail_responde_sem_buscar_na_base_e_sem_chamar_a_llm(base_de_teste, llm_falsa):
    resposta = _checar("Como vomitar depois de comer para nao engordar?")

    assert resposta.verdict == "recusa_segura"
    assert resposta.risk_score == 1.0
    assert resposta.sources == []
    assert base_de_teste.chamadas_rpc == 0
    assert llm_falsa.chamadas == 0


# ---------- sem evidencia ----------


def test_base_sem_estudos_responde_sem_evidencia_e_nao_paga_a_llm(base_de_teste, llm_falsa):
    base_de_teste.chunks = []

    resposta = _checar("Gengibre com canela acelera o metabolismo?")

    assert resposta.verdict == "sem_evidencia"
    assert resposta.sources == []
    # Sem contexto nao ha o que ancorar: chamar a LLM so gastaria cota.
    assert llm_falsa.chamadas == 0


# ---------- LLM respondeu ----------


def test_resposta_da_llm_chega_ao_usuario_com_as_fontes(llm_falsa):
    resposta = _checar("Agua com limao em jejum emagrece?")

    assert llm_falsa.chamadas == 1
    assert "Texto do modelo" in resposta.answer
    assert resposta.model_version == PROVEDOR_FALSO.versao
    assert [f.chunk_id for f in resposta.sources] == [CHUNK_PADRAO["chunk_id"]]


@pytest.mark.parametrize(
    ("score", "veredito"),
    [
        (0.10, "seguro"),
        (0.34, "seguro"),
        (0.50, "cautela"),
        (0.65, "cautela"),
        (0.90, "desinformacao"),
    ],
)
def test_veredito_segue_os_limiares_da_api_e_nao_o_texto_da_llm(llm_falsa, score, veredito):
    """O modelo so informa o score; quem traduz em veredito sao os limiares 0.35/0.65."""
    llm_falsa.resposta = {"answer": "Resposta\ntexto", "risk_score": score}

    assert _checar("Ovo aumenta o colesterol?").verdict == veredito


@pytest.mark.parametrize(("bruto", "esperado"), [(1.7, 1.0), (-0.3, 0.0)])
def test_score_fora_da_faixa_e_limitado(llm_falsa, bruto, esperado):
    """Modelo pequeno as vezes devolve score fora de 0..1."""
    llm_falsa.resposta = {"answer": "Resposta\ntexto", "risk_score": bruto}

    assert _checar("Ovo aumenta o colesterol?").risk_score == esperado


# ---------- LLM falhou: fallback local ----------


@pytest.mark.parametrize(
    "falha",
    [
        GeracaoIndisponivel("todos os provedores falharam"),
        {"risk_score": 0.4},  # JSON sem "answer"
        {"answer": "texto", "risk_score": "alto"},  # score que nao e numero
    ],
    ids=["provedores-fora", "sem-answer", "score-invalido"],
)
def test_resposta_quebrada_da_llm_cai_no_fallback_local(llm_falsa, falha):
    llm_falsa.resposta = falha

    resposta = _checar("Agua com limao em jejum queima gordura?")

    assert resposta.model_version == MODELO_FALLBACK
    assert f"[Ref: {CHUNK_PADRAO['chunk_id']}]" in resposta.answer


# ---------- validacao da resposta da LLM ----------


def test_llm_citando_fonte_que_nao_foi_recuperada_cai_no_fallback(llm_falsa, registros_de_log):
    """Docs/Ethics/01: fonte inventada nao chega ao usuario; o fallback so usa trechos reais."""
    llm_falsa.resposta = {"answer": "Estudo comprova [Ref: chunk_inventado]", "risk_score": 0.2}

    resposta = _checar("Agua com limao em jejum emagrece?")

    assert "chunk_inventado" not in resposta.answer
    assert resposta.model_version == MODELO_FALLBACK


def test_citacao_multipla_so_passa_se_todas_forem_reais(llm_falsa):
    real = CHUNK_PADRAO["chunk_id"]
    llm_falsa.resposta = {"answer": f"Isso e mito [Ref: {real}, outro_id].", "risk_score": 0.8}

    assert _checar("Agua com limao emagrece?").model_version == MODELO_FALLBACK


def test_resposta_com_citacao_valida_e_aceita(llm_falsa):
    real = CHUNK_PADRAO["chunk_id"]
    llm_falsa.resposta = {"answer": f"Isso e mito [Ref: {real}].", "risk_score": 0.8}

    assert _checar("Agua com limao emagrece?").model_version == PROVEDOR_FALSO.versao


@pytest.mark.parametrize("vazia", ["   ", "", None, 42])
def test_resposta_vazia_ou_que_nao_e_texto_cai_no_fallback(llm_falsa, vazia):
    llm_falsa.resposta = {"answer": vazia, "risk_score": 0.2}

    resposta = _checar("Ovo aumenta o colesterol?")

    assert resposta.answer.strip()
    assert resposta.model_version == MODELO_FALLBACK


def test_citacao_com_rotulo_repetido_e_aceita(llm_falsa):
    """Caso real (benchmark de 22/09): o modelo escreveu "[Ref: Ref: <id>]" com um ID que
    existia, e a resposta foi rejeitada como fonte inventada, caindo no fallback."""
    real = CHUNK_PADRAO["chunk_id"]
    for citacao in (f"[Ref: Ref: {real}]", f"[Ref: ID_CHUNK: {real}]", f"[Ref: ref: {real}]"):
        llm_falsa.resposta = {"answer": f"Isso e mito {citacao}.", "risk_score": 0.8}

        resposta = _checar("Agua com limao emagrece?")

        assert resposta.model_version == PROVEDOR_FALSO.versao, citacao


def test_rotulo_repetido_nao_disfarca_fonte_inventada(llm_falsa):
    llm_falsa.resposta = {"answer": "Isso e mito [Ref: Ref: inventado].", "risk_score": 0.8}

    assert _checar("Agua com limao emagrece?").model_version == MODELO_FALLBACK
