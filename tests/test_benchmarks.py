"""Testes das ferramentas de avaliacao (issue #9).

As metricas sao testadas como funcoes puras; o executor e o estresse rodam em
processo contra a aplicacao, com poucos casos, para caber no CI.
"""

import asyncio
import time

import pytest

from APP.model import pipeline as modulo_pipeline
from APP.routers import check_claim as modulo_rota
from benchmarks import avaliar_pipeline, estresse
from benchmarks.metricas import Caso, calcular, f_beta, percentil


def _caso(id_, esperado, classe, obtido, status=200, latencia=100.0, tipo="mito"):
    return Caso(id_, tipo, esperado, classe, status, obtido, 0.5, latencia)


# ---------- metricas ----------


def test_percentil_por_interpolacao():
    assert percentil([10, 20, 30, 40], 50) == 25
    assert percentil([10, 20, 30, 40], 100) == 40
    assert percentil([], 95) is None


def test_f2_pesa_recall_mais_que_precisao():
    assert f_beta(1.0, 0.5) < f_beta(0.5, 1.0)
    assert f_beta(0.0, 0.0) == 0.0


def test_matriz_binaria_e_metricas():
    casos = [
        _caso("1", "desinformacao", 1, "desinformacao"),  # TP
        _caso("2", "desinformacao", 1, "seguro"),  # FN
        _caso("3", "seguro", 0, "cautela"),  # FP
        _caso("4", "seguro", 0, "seguro"),  # TN
    ]

    r = calcular(casos)

    assert r["matriz_binaria"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert r["recall"] == 0.5
    assert r["precisao"] == 0.5
    assert r["acuracia_exata"] == 0.5


def test_falha_de_requisicao_fica_fora_da_matriz():
    """Um 429 nao pode virar 'previu seguro' e inflar os falsos negativos."""
    casos = [
        _caso("1", "desinformacao", 1, "desinformacao"),
        _caso("2", "desinformacao", 1, None, status=429),
    ]

    r = calcular(casos)

    assert r["matriz_binaria"]["fn"] == 0
    assert r["recall"] == 1.0
    assert r["falhas"] == [{"id": "2", "status": 429}]


def test_taxa_de_recusa_segura_considera_so_red_teaming():
    casos = [
        _caso("1", "recusa_segura", 1, "recusa_segura", tipo="red_teaming_jejum"),
        _caso("2", "recusa_segura", 1, "cautela", tipo="red_teaming_purgacao"),
        _caso("3", "seguro", 0, "seguro", tipo="fato_seguro"),
    ]

    assert calcular(casos)["taxa_recusa_segura"] == 0.5


def test_metas_reprovadas_sao_listadas():
    relatorio = {"recall": 0.9, "f2": 0.95, "taxa_recusa_segura": 1.0}

    reprovadas = avaliar_pipeline.verificar_metas(relatorio, 0.95, 0.90, 1.0)

    assert reprovadas == ["recall 0.9000 < 0.95"]


# ---------- executor do benchmark ----------


def test_benchmark_com_mais_de_10_casos_nao_bate_no_rate_limit():
    """Regressao: com token unico, o 11o caso recebia 429 e o script quebrava."""
    dataset = avaliar_pipeline.carregar_dataset(avaliar_pipeline.DATASET_PADRAO)
    ampliado = dataset + [{**c, "id": f"{c['id']}-bis"} for c in dataset]
    assert len(ampliado) > 10

    casos = asyncio.run(avaliar_pipeline.executar(ampliado))

    assert all(c.status == 200 for c in casos)
    assert calcular(casos)["falhas"] == []


def test_benchmark_devolve_codigo_de_saida_para_o_ci(tmp_path):
    saida = tmp_path / "relatorio.json"

    codigo = avaliar_pipeline.main(["--saida", str(saida), "--min-recall", "1.01"])

    assert codigo == 1  # meta impossivel: o gate precisa reprovar
    assert saida.exists()


# ---------- estresse ----------


def test_estresse_em_processo_sem_falhas():
    relatorio = asyncio.run(estresse.executar(usuarios=5, requisicoes=10))

    assert relatorio["sucesso"] == 10
    assert relatorio["latencia_ms"]["p95"] is not None


@pytest.mark.parametrize("usuarios", [4])
def test_estresse_detecta_que_o_health_segue_respondendo_sob_carga(monkeypatch, usuarios):
    """Com o pipeline lento, o /health tem que continuar rapido: e o que prova
    que o conserto do event loop aguenta carga concorrente, nao so um caso isolado."""
    original = modulo_pipeline.executar_pipeline_de_checagem

    def lento(*args, **kwargs):
        time.sleep(0.4)
        return original(*args, **kwargs)

    monkeypatch.setattr(modulo_rota, "executar_pipeline_de_checagem", lento)

    relatorio = asyncio.run(estresse.executar(usuarios=usuarios, requisicoes=usuarios))

    assert relatorio["sucesso"] == usuarios
    assert relatorio["health_ms"]["amostras"] > 0
    assert relatorio["health_ms"]["max"] < 400


def test_sla_violado_e_reportado():
    relatorio = {
        "requisicoes": 10,
        "sucesso": 9,
        "latencia_ms": {"p95": 6200.0},
        "health_ms": {"max": 3000.0},
    }

    violacoes = estresse.avaliar_sla(relatorio, sla_p95_ms=5000, sla_health_ms=1000)

    assert len(violacoes) == 3


# ---------- origem das respostas e repeticoes ----------


def test_relatorio_separa_respostas_da_llm_do_fallback():
    """Acerto do fallback nao mede o prompt: na comparacao v1 x v2 de 22/09, dois acertos
    atribuidos a v1 vieram do fallback."""
    casos = [
        Caso("1", "mito", "desinformacao", 1, 200, "desinformacao", 0.8, 100.0, "gemini/x"),
        Caso("2", "mito", "cautela", 1, 200, "cautela", 0.5, 100.0, "fallback-local@v2"),
        Caso("3", "red_teaming", "recusa_segura", 1, 200, "recusa_segura", 1.0, 1.0, "guardrail@e"),
    ]

    assert calcular(casos)["origem"] == {"llm": 1, "fallback": 1, "guardrail": 1}


def test_repeticoes_rodam_o_dataset_varias_vezes():
    dataset = avaliar_pipeline.carregar_dataset(avaliar_pipeline.DATASET_PADRAO)[:3]

    casos = asyncio.run(avaliar_pipeline.executar(dataset, repeticoes=2))

    assert [c.id for c in casos] == [f"{d['id']}#{r}" for r in (1, 2) for d in dataset]


def test_consistencia_aponta_caso_que_mudou_de_veredito(capsys):
    casos = [
        {"id": "BM-09#1", "obtido": "seguro"},
        {"id": "BM-09#2", "obtido": "cautela"},
        {"id": "BM-02#1", "obtido": "seguro"},
        {"id": "BM-02#2", "obtido": "seguro"},
    ]

    avaliar_pipeline._imprimir_consistencia(casos)

    saida = capsys.readouterr().out
    assert "1 de 2" in saida
    assert "BM-09: seguro, cautela" in saida
