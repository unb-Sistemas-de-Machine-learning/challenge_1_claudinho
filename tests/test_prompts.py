"""Prompts do gerador (APP/model/prompts.py).

O texto do prompt nao e testavel por qualidade aqui (isso e o benchmarks/comparar_prompts.py,
com LLM de verdade e leitura humana). O que se testa e o que quebraria em silencio.
"""

import json
import re

import pytest

from APP.config import obter_settings
from APP.model import generator, prompts
from APP.model.pipeline import executar_pipeline_de_checagem
from APP.schemas import CheckClaimRequest
from tests._dubles import PROVEDOR_FALSO


@pytest.fixture
def prompts_enviados(monkeypatch):
    """Captura o que o gerador manda para a LLM."""
    capturados = []

    def falsa(sistema, usuario, *_args, **_kwargs):
        capturados.append({"sistema": sistema, "usuario": usuario})
        return {"answer": "Isso é mito [Ref: chunk_teste_01].", "risk_score": 0.8}, PROVEDOR_FALSO

    monkeypatch.setattr(generator, "gerar_json", falsa)
    return capturados


def _checar():
    return executar_pipeline_de_checagem(
        CheckClaimRequest(input_type="text", text="Agua com limao emagrece?"),
        obter_settings(),
        0,
        "trace",
    )


def test_versao_ativa_e_a_v2_e_vai_para_a_resposta(prompts_enviados):
    """O prompt_version no log e o que permite comparar qualidade entre versoes."""
    assert _checar().prompt_version == "rag-v2.0"


@pytest.mark.parametrize("versao", list(prompts.VERSOES))
def test_tag_citada_no_prompt_e_a_mesma_que_envolve_os_estudos(
    monkeypatch, prompts_enviados, versao
):
    """Se o prompt manda ler <estudos> e o gerador envia <contexto>, o modelo ignora os
    estudos e responde de cabeca. Nada quebraria: so a resposta ficaria sem base."""
    monkeypatch.setattr(prompts, "VERSAO_ATIVA", versao)
    _, tag = prompts.VERSOES[versao]

    _checar()

    enviado = prompts_enviados[-1]
    assert f"<{tag}>" in enviado["sistema"]
    assert f"<{tag}>" in enviado["usuario"] and f"</{tag}>" in enviado["usuario"]


def test_exemplo_de_json_da_v2_e_json_valido():
    """O exemplo da v1 tinha um comentario // e era JSON invalido; modelo pequeno copia."""
    exemplo = re.findall(r"\{\"answer\".*\}", prompts.SISTEMA_RAG_V2)[-1]

    assert set(json.loads(exemplo)) == {"answer", "risk_score"}


def test_v2_nao_impoe_o_molde_fixo_da_v1():
    for marca in ("Entendi assim", "A ciência indica que", "Linha 1", "Título de tom"):
        assert marca not in prompts.SISTEMA_RAG_V2


def test_v2_nao_diz_que_o_assistente_e_o_lucas():
    """Lucas e a persona de quem pergunta (Docs/User/01), nao do assistente."""
    assert "Lucas" not in prompts.SISTEMA_RAG_V2


def test_v2_e_mais_curta_que_a_v1():
    """Modelo pequeno (qwen2.5:3b no Ollama) segue pior um prompt longo."""
    assert len(prompts.SISTEMA_RAG_V2.split()) <= len(prompts.SISTEMA_RAG_V1.split())


def test_resposta_sem_evidencia_segue_o_estilo_da_v2(base_de_teste, prompts_enviados):
    base_de_teste.chunks = []

    resposta = _checar()

    assert resposta.answer == generator.RESPOSTA_SEM_EVIDENCIA
    assert resposta.answer.startswith("Ainda não temos estudos")
    assert "Entendi assim" not in resposta.answer
    assert prompts_enviados == []  # sem estudos, nada vai para a LLM


def test_v2_1_existe_mas_nao_esta_ativa():
    """A troca de versao e decisao do grupo, depois de comparar no benchmark."""
    assert "rag-v2.1" in prompts.VERSOES
    assert prompts.VERSAO_ATIVA == "rag-v2.0"


def test_nenhum_prompt_copia_perguntas_do_benchmark():
    """Se o prompt contem trechos das perguntas do benchmark, o modelo acerta por memoria e
    o benchmark deixa de medir a qualidade real. Qualquer sequencia de 4 palavras igual a
    uma pergunta do benchmark reprova."""
    from benchmarks.avaliar_pipeline import DATASET_PADRAO, carregar_dataset

    def quadrigramas(texto: str) -> set[tuple[str, ...]]:
        palavras = re.findall(r"\w+", texto.lower())
        return {tuple(palavras[i : i + 4]) for i in range(len(palavras) - 3)}

    perguntas = set().union(*(quadrigramas(c["entrada"]) for c in carregar_dataset(DATASET_PADRAO)))
    for versao, (texto, _tag) in prompts.VERSOES.items():
        copiados = quadrigramas(texto) & perguntas
        assert not copiados, f"{versao} copia do benchmark: {sorted(copiados)[:3]}"
