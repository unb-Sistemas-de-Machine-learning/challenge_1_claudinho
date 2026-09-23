"""Testes unitários do classificador de padrões semânticos e evidências (classifier.py).

Verifica a cobertura dos padrões semânticos (Docs/Model/03 e Docs/Model/04):
- Mitos confirmados de internet (PADROES_MITO_CONFIRMADO) -> 0.78, "desinformacao"
- Temas de cautela e dietas restritivas (PADROES_TEMA_CAUTELA) -> 0.48, "cautela"
- Consenso científico protetor e seguro (PADROES_CONSENSO_SEGURO) -> 0.18, "seguro"
- Dúvidas clínicas abertas/nuances -> None (deixa a decisão para a LLM ancorada)
- Avaliação heurística a partir dos artigos do Supabase
"""

from datetime import date

import pytest

from APP.model.classifier import (
    SCORE_CAUTELA,
    SCORE_MITO,
    SCORE_PADRAO_INCONCLUSIVO,
    SCORE_SEGURO,
    calcular_risco_evidencia,
    classificar_padrao_semantico,
    classificar_por_fontes,
)
from APP.schemas import Fonte


def _fonte(titulo: str) -> Fonte:
    return Fonte(
        chunk_id="c1",
        title=titulo,
        authors="Autor, A.",
        journal="Rev. Nutr.",
        published_at=date(2022, 1, 1),
        doi="10.1590/test",
        excerpt="Trecho de teste.",
    )


# 1. Bateria de mitos confirmados
CASOS_MITO = [
    "Água com limão em jejum queima gordura e seca a barriga?",
    "Tomar shot de vinagre de maçã em jejum desinflama o corpo ou é meme?",
    "Comer carboidrato após as 18h engorda mais do que no almoço?",
    "Cortar carboidrato no jantar porque carboidrato à noite vira gordura",
    "Pão é veneno que inflama o corpo todo?",
    "Glúten inflama qualquer pessoa e deve ser banido da dieta?",
    "Fruta depois do almoço apodrece no estômago se comer de sobremesa?",
    "A frutose das frutas é veneno para o fígado?",
    "Fazer a dieta do ovo para secar 5kg rápido funciona?",
    "Chá detox seca barriga e elimina gordura do fígado?",
    "Água alcalina altera o pH do sangue e previne doenças?",
    "Alimentos com caloria negativa gastam mais calorias do que fornecem?",
    "Açúcar mascavo não engorda nada comparado ao branco?",
    "Tomar óleo de coco em jejum derrete a gordura corporal?",
]


@pytest.mark.parametrize("frase", CASOS_MITO)
def test_classifica_mitos_confirmados(frase):
    resultado = classificar_padrao_semantico(frase)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "desinformacao"
    assert score == SCORE_MITO
    assert score > 0.65


# 2. Bateria de temas de cautela
CASOS_CAUTELA = [
    "Dieta low carb é indicada para todas as pessoas sem restrição?",
    "Cortar carboidrato é obrigatório para conseguir emagrecer?",
    "Jejum intermitente é superior a qualquer dieta e cura tudo?",
    "Suplementação de creatina é indispensável para todo mundo?",
    "Dieta cetogênica contínua para qualquer pessoa sem acompanhamento?",
    "Adoçantes artificiais causam câncer em qualquer quantidade?",
    "Cortar toda gordura da alimentação é o mais saudável?",
]


@pytest.mark.parametrize("frase", CASOS_CAUTELA)
def test_classifica_temas_de_cautela(frase):
    resultado = classificar_padrao_semantico(frase)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "cautela"
    assert score == SCORE_CAUTELA
    assert 0.35 <= score <= 0.65


# 3. Bateria de consenso científico seguro
CASOS_SEGURO = [
    "Comer arroz e feijão na proporção adequada fornece proteínas e nutrientes essenciais?",
    "A hidratação diária com água auxilia na digestão e no funcionamento intestinal?",
    "Consumir frutas e vegetais diariamente fornece fibras e vitaminas protetoras?",
    "Fazer reeducação alimentar e dieta flexível gera hábitos sustentáveis?",
    "Comer devagar com mastigação lenta melhora a saciedade?",
    "Manter um déficit calórico moderado é a forma mais sustentável de emagrecer?",
    "Consumo regular de leguminosas e azeite de oliva protege a saúde cardiovascular?",
]


@pytest.mark.parametrize("frase", CASOS_SEGURO)
def test_classifica_consenso_seguro(frase):
    resultado = classificar_padrao_semantico(frase)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "seguro"
    assert score == SCORE_SEGURO
    assert score < 0.35


# 4. Questões que NÃO devem casar com padrões rígidos (devem retornar None)
CASOS_NEUTROS = [
    "Ovo aumenta o colesterol no sangue?",
    "Qual a quantidade diária recomendada de água para adultos?",
    "Qual a diferença entre carboidrato simples e complexo?",
    "Praticar musculação três vezes por semana é suficiente?",
    "Como calcular o índice de massa corporal?",
    "",
]


@pytest.mark.parametrize("frase", CASOS_NEUTROS)
def test_questoes_abertas_nao_casam_com_padroes(frase):
    assert classificar_padrao_semantico(frase) is None


# 5. Avaliação heurística a partir dos artigos no Supabase
def test_classificacao_por_fontes_com_artigos_de_desinformacao():
    fontes = [
        _fonte("Desinformação e infodemia sobre nutrição em redes sociais"),
        _fonte("Terrorismo nutricional e dietas da moda no Instagram"),
    ]
    resultado = classificar_por_fontes(fontes)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "desinformacao"
    assert score == 0.72


def test_classificacao_por_fontes_com_artigos_de_cautela():
    fontes = [
        _fonte("Efeitos da dieta low-carb em longo prazo"),
        _fonte("Restrição alimentar e riscos de transtorno alimentar"),
    ]
    resultado = classificar_por_fontes(fontes)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "cautela"
    assert score == 0.45


def test_classificacao_por_fontes_com_artigos_de_seguranca():
    fontes = [
        _fonte("Reeducação alimentar e promoção da saúde mental"),
        _fonte("O Guia Alimentar para a População Brasileira"),
    ]
    resultado = classificar_por_fontes(fontes)

    assert resultado is not None
    score, categoria = resultado
    assert categoria == "seguro"
    assert score == 0.20


def test_classificacao_por_fontes_sem_termos_chave_retorna_none():
    fontes = [_fonte("Análise físico-química de maçãs gala")]
    assert classificar_por_fontes(fontes) is None


def test_calcular_risco_evidencia_fallback_inconclusivo():
    score, categoria = calcular_risco_evidencia("Dúvida qualquer sem padrão", [], [])
    assert score == SCORE_PADRAO_INCONCLUSIVO
    assert categoria == "cautela"
