"""Disclaimers e alertas homologados pela frente de Etica.

Os textos sao copiados LITERALMENTE de Docs/Ethics/03_transparencia_e_disclaimers.md
(secoes 2.1 a 2.3) e da tabela de filtros de Docs/Ethics/02_grupos_de_risco_e_filtros.md.
Nao reescreva aqui: mude no documento e copie. tests/test_disclaimers.py confere cada texto
contra o documento, e falha se os dois divergirem.

Regras aplicadas (Docs/Ethics/02, tabela de filtros):
- Toda resposta de checagem leva o disclaimer curto (Docs/Ethics/03, secao 2.1).
- Veredito "cautela" leva o aviso de evidencia limitada (secao 2.3).
- Mencao a gestacao ou amamentacao leva o aviso para gestantes e lactantes.
- Mencao a condicao clinica cronica leva o aviso de publicos com necessidades especiais.
- Menor de 18 anos: recusa de servico (LGPD, Art. 14).
"""

import re

# Docs/Ethics/03, secao 2.1: obrigatorio no rodape de TODAS as respostas de checagem.
CURTO = (
    "Esta análise tem caráter exclusivamente informativo e é gerada por inteligência "
    "artificial com base em literatura científica disponível. Não substitui o diagnóstico, "
    "aconselhamento ou tratamento de um nutricionista ou médico."
)

# Docs/Ethics/03, secao 2.3: situacoes de incerteza cientifica.
EVIDENCIA_LIMITADA = (
    "A alegação analisada aborda um tema onde a ciência atual apresenta estudos "
    "inconclusivos, de baixa qualidade metodológica ou com opiniões divergentes na comunidade "
    "acadêmica. O resultado apresentado reflete o consenso provisório da literatura e não deve "
    "ser tomado como verdade definitiva."
)

# Docs/Ethics/03, secao 2.2, item 4.
GESTANTES_E_LACTANTES = (
    "Se você está grávida ou amamentando, não siga recomendações genéricas de internet. A "
    "nutrição gestacional exige acompanhamento pré-natal individualizado para evitar riscos "
    "ao desenvolvimento fetal."
)

# Docs/Ethics/03, secao 2.2, item 3.
CONDICOES_CLINICAS = (
    "Se você possui condições clínicas (como diabetes, hipertensão ou doença celíaca), "
    "gestação ou histórico de transtornos alimentares, consulte sempre seu profissional de "
    "referência."
)

# Docs/Ethics/02, tabela de filtros, linha "Menores de 18 anos".
MENOR_DE_IDADE = (
    "O uso deste aplicativo é restrito a maiores de 18 anos (LGPD Art. 14). Recomendamos "
    "consultar um nutricionista com seu responsável legal."
)

IDADE_MINIMA = 18

_GESTACAO = re.compile(
    r"\b(gr[aá]vida|gestante|gesta[cç][aã]o|gravidez|amamenta\w*|lactante|"
    r"estou esperando (um )?beb[eê])\b"
)
_CONDICAO_CRONICA = re.compile(
    r"\b(diab[eé]t\w*|hipertens\w*|press[aã]o alta|doen[cç]a renal|insufici[eê]ncia renal|"
    r"renal cr[oô]nic\w*|cel[ií]ac\w*)\b"
)
_NUMERO_POR_EXTENSO = (
    "dez|onze|doze|treze|quatorze|catorze|quinze|dezesseis|dezessete|"
    "um|dois|tr[eê]s|quatro|cinco|seis|sete|oito|nove"
)
# Primeira pessoa ("tenho 15 anos"), e nao "meu filho tem 15 anos": quem pergunta sobre o
# filho e um adulto. "Tenho 15 anos de diabetes" e duracao, nao idade.
_MENOR = re.compile(
    r"\b(tenho|fiz|vou fazer|completei)\s+"
    rf"([1-9]|1[0-7]|{_NUMERO_POR_EXTENSO})\s+anos\b(?!\s+(de|com|que)\b)"
    r"|\bsou menor de idade\b"
)


def _normalizar(texto: str) -> str:
    return texto.lower()


def e_menor_de_idade(texto: str) -> bool:
    """A pessoa declara, no proprio texto, ter menos de 18 anos."""
    return bool(_MENOR.search(_normalizar(texto)))


def montar_disclaimer(veredito: str, texto_do_usuario: str) -> str:
    """Disclaimer curto obrigatorio, mais os avisos que a situacao exige."""
    texto = _normalizar(texto_do_usuario)
    partes = [CURTO]
    if veredito == "cautela":
        partes.append(EVIDENCIA_LIMITADA)
    if _GESTACAO.search(texto):
        partes.append(GESTANTES_E_LACTANTES)
    elif _CONDICAO_CRONICA.search(texto):
        # O aviso de condicoes clinicas ja cita gestacao; com os dois, ficaria repetido.
        partes.append(CONDICOES_CLINICAS)
    return "\n\n".join(partes)
