"""Fallback local: quando nenhuma LLM responde, a resposta ainda precisa ser humana,
seguir a estrutura da persona e ficar ancorada nos trechos recuperados."""

import re
from datetime import date

import pytest

from APP.config import Settings
from APP.model import generator
from APP.model.llm import GeracaoIndisponivel
from APP.model.resposta_local import MODEL_VERSION, montar_resposta_local, resumir_trecho
from APP.schemas import Fonte

PERGUNTA = "Água com limão em jejum queima gordura?"
TRECHO = (
    "ções avaliadas. Não foram observadas diferenças significativas no gasto energético "
    "entre os grupos. A redução do inchaço esteve associada à ingestão de água, e não ao "
    "limão em si. Os autores recomendam"
)
EMOJI = re.compile("[\U0001f300-\U0001faff\u2600-\u27bf]")


def _fonte(chunk_id="c1", titulo="Efeitos metabólicos de compostos cítricos"):
    return Fonte(
        chunk_id=chunk_id,
        title=titulo,
        authors="Silva, R.",
        journal="Rev. Nutr.",
        published_at=date(2021, 6, 1),
        doi="10.1590/x",
        excerpt=TRECHO[:300],
    )


def _settings(**extra):
    # URL que NAO e a de teste: senao o gerador cai no atalho de testes antes do fallback.
    base = {"supabase_url": "https://real.supabase.co", "supabase_key": "x", "app_env": "local"}
    return Settings(**{**base, **extra})


# ---------- texto ----------


ABERTURAS_POSSIVEIS = {
    "desinformacao": ("Isso é mito", "Não é bem assim", "Essa ideia circula"),
    "cautela": ("Depende", "Não dá para dizer", "Em parte"),
    "seguro": ("Sim, isso", "Pode confiar", "É verdade"),
}


@pytest.mark.parametrize("veredito", ["desinformacao", "cautela", "seguro"])
def test_veredito_vem_na_primeira_frase(veredito):
    """Docs/User/01, secao 2.2, item 1: o Lucas decide pela primeira frase se continua."""
    texto = montar_resposta_local(veredito, PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert texto.startswith(ABERTURAS_POSSIVEIS[veredito])


@pytest.mark.parametrize("veredito", ["desinformacao", "cautela", "seguro"])
def test_titulo_do_estudo_fica_fora_do_texto(veredito):
    """Item 3: a fonte fica na secao de fontes do app; no texto, so o [Ref: ID]."""
    texto = montar_resposta_local(veredito, PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert "[Ref: c1]." in texto
    assert "Efeitos metabólicos" not in texto


@pytest.mark.parametrize("veredito", ["desinformacao", "cautela", "seguro"])
def test_sem_as_marcas_do_formato_antigo(veredito):
    texto = montar_resposta_local(veredito, PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert not texto.startswith("Resposta")
    assert "Entendi assim" not in texto
    assert "A ciência indica" not in texto
    assert "\n" not in texto


@pytest.mark.parametrize("veredito", ["desinformacao", "cautela", "seguro"])
def test_resposta_e_curta(veredito):
    texto = montar_resposta_local(veredito, PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert len(texto.split()) <= 110


def test_resposta_nao_usa_emojis():
    texto = montar_resposta_local("desinformacao", PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert not EMOJI.search(texto)


def test_so_cita_chunks_que_vieram_da_base():
    fontes = [_fonte("c1"), _fonte("c2", "Outro estudo")]
    texto = montar_resposta_local("cautela", PERGUNTA, fontes, {"c1": TRECHO, "c2": TRECHO})

    assert set(re.findall(r"\[Ref: (\w+)\]", texto)) <= {"c1", "c2"}


def test_sem_trechos_uteis_nao_inventa_conteudo():
    # Nem o chunk nem o excerpt da fonte trazem texto aproveitavel.
    fonte_vazia = _fonte().model_copy(update={"excerpt": ""})

    texto = montar_resposta_local("cautela", PERGUNTA, [fonte_vazia], {"c1": ""})

    assert "não são claros o bastante" in texto
    assert "[Ref:" not in texto


def test_mesma_pergunta_recebe_a_mesma_resposta():
    """Deterministico: a auditoria pelo trace_id precisa conseguir reproduzir o texto."""
    a = montar_resposta_local("seguro", PERGUNTA, [_fonte()], {"c1": TRECHO})
    b = montar_resposta_local("seguro", PERGUNTA, [_fonte()], {"c1": TRECHO})

    assert a == b


# ---------- limpeza dos trechos ----------


def test_trecho_que_comeca_no_meio_da_frase_perde_o_fragmento():
    assert resumir_trecho(TRECHO).startswith("não foram observadas")


def test_trecho_que_termina_no_meio_da_frase_perde_o_fragmento():
    assert "recomendam" not in resumir_trecho(TRECHO)
    assert resumir_trecho(TRECHO).endswith("limão em si.")


def test_sigla_no_inicio_nao_vira_minuscula():
    assert resumir_trecho("IMC acima de 30 foi associado a maior risco.").startswith("IMC")


def test_trecho_longo_e_cortado_em_fim_de_frase():
    longo = "Primeira frase completa sobre o tema. " * 20

    resumo = resumir_trecho(longo)

    assert len(resumo) <= 363
    assert resumo.endswith(".")


# ---------- integracao com o gerador ----------


def test_sem_provedor_configurado_usa_o_fallback_em_vez_de_erro():
    resposta, score, veredito, modelo, _ = generator.gerar_resposta_grounded(
        "agua com limao em jejum queima gordura",
        [_fonte()],
        [{"chunk_id": "c1", "conteudo": TRECHO}],
        _settings(),
        PERGUNTA,
    )

    assert modelo == MODEL_VERSION
    assert veredito == "desinformacao"
    assert score > 0.65
    assert "[Ref: c1]" in resposta


def test_provedores_fora_do_ar_caem_no_fallback(monkeypatch):
    def todos_falham(*_args, **_kwargs):
        raise GeracaoIndisponivel("todos os provedores falharam")

    monkeypatch.setattr(generator, "gerar_json", todos_falham)

    *_, modelo, _versao = generator.gerar_resposta_grounded(
        "agua com limao",
        [_fonte()],
        [{"chunk_id": "c1", "conteudo": TRECHO}],
        _settings(gemini_api_key="chave"),
        PERGUNTA,
    )

    assert modelo == MODEL_VERSION


def test_fallback_vale_com_dados_sensiveis_e_sem_modelo_proprio():
    """Sem Ollama configurado, dado sensivel nao pode ir para o Gemini; o fallback,
    que e local, continua respondendo em vez de devolver erro."""
    *_, modelo, _versao = generator.gerar_resposta_grounded(
        "agua com limao",
        [_fonte()],
        [{"chunk_id": "c1", "conteudo": TRECHO}],
        _settings(gemini_api_key="chave"),
        PERGUNTA,
        dados_sensiveis=True,
    )

    assert modelo == MODEL_VERSION
