"""Script de comparacao de prompts (benchmarks/comparar_prompts.py)."""

import pytest

from APP.model import generator, prompts
from benchmarks import comparar_prompts
from tests._dubles import CHUNK_PADRAO, PROVEDOR_FALSO

REF = f"[Ref: {CHUNK_PADRAO['chunk_id']}]"


def test_detecta_marcas_de_resposta_robotica():
    texto = "Resposta sobre o mito\nCompreendo.\nEntendi assim: x\n\nCom base nos fragmentos..."

    a = comparar_prompts.analisar(texto, set())

    assert a["comeca_com_titulo"]
    assert a["molde_antigo"] == ["Entendi assim"]
    assert a["vazamentos"] == ["fragmento"]


def test_detecta_referencia_a_estudo_que_nao_foi_recuperado():
    a = comparar_prompts.analisar("Isso é mito [Ref: c1]. Veja [Ref: inventado].", {"c1"})

    assert a["refs"] == 2
    assert a["refs_inventadas"] == ["inventado"]


def test_resposta_limpa_nao_gera_alerta():
    a = comparar_prompts.analisar(
        f"Isso é mito. Nos estudos, não houve efeito {REF}.", {"chunk_teste_01"}
    )

    assert not (a["comeca_com_titulo"] or a["molde_antigo"] or a["vazamentos"])
    assert a["refs_inventadas"] == []


@pytest.fixture
def llm_por_versao(monkeypatch):
    """LLM falsa que responde no estilo de cada versao, para o relatorio ter contraste."""

    def falsa(sistema, _usuario, *_a, **_k):
        if "Entendi assim" in sistema:
            texto = f"Resposta sobre o mito\nCompreendo.\nEntendi assim: x\n\nNão {REF}."
        else:
            texto = f"Isso é mito. Nos estudos, não houve efeito {REF}."
        return {"answer": texto, "risk_score": 0.8}, PROVEDOR_FALSO

    monkeypatch.setattr(generator, "gerar_json", falsa)


def test_relatorio_compara_as_versoes_e_restaura_a_ativa(tmp_path, llm_por_versao):
    saida = tmp_path / "comparacao.md"
    ativa_antes = prompts.VERSAO_ATIVA

    codigo = comparar_prompts.main(["--limite", "2", "--saida", str(saida)])

    relatorio = saida.read_text(encoding="utf-8")
    assert codigo == 0
    assert "| com_molde_antigo | " in relatorio
    assert "**rag-v1.0**" in relatorio and "**rag-v2.0**" in relatorio
    assert "molde antigo: Entendi assim" in relatorio
    # O script troca a versao ativa durante a execucao; ela tem que voltar ao normal.
    assert prompts.VERSAO_ATIVA == ativa_antes


def test_versao_inexistente_e_recusada(tmp_path):
    assert comparar_prompts.main(["--versoes", "rag-v9", "--saida", str(tmp_path / "x.md")]) == 2
