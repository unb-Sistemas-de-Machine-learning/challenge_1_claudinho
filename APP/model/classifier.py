"""Classificador de Risco e Veredito baseado nas Evidências do Supabase.

Baseado em:
- Docs/Model/01_metricas_e_avaliacao.md (Limiares de decisão e matriz de custos)
- Docs/Model/03_processamento_linguagem_internet.md (Sinais semânticos de mitos)
- Docs/Model/04_treinamento_e_classificador_risco.md (Calibração e priors)
- Docs/Data/02_armazenamento_e_estrutura.md (Classificação por evidência científica)
"""

import re

from APP.schemas import Fonte

# Escores calibrados de acordo com Docs/Model/01 e Docs/Model/04
SCORE_MITO = 0.78
SCORE_CAUTELA = 0.48
SCORE_SEGURO = 0.18
SCORE_PADRAO_INCONCLUSIVO = 0.38

# 1. Padrões semânticos de mitos de internet consolidados (Docs/Model/03)
PADROES_MITO_CONFIRMADO = [
    # Queima milagrosa com limão, vinagre ou shots em jejum
    r"(?:queima|queimar|derreter)\s+gordura.*(?:lim[aã]o|jejum|vinagre|shot)",
    r"(?:lim[aã]o|vinagre|shot\s+matinal).*(?:queima|desincha|desinflama|secar|emagrec)",
    # Carboidrato noturno / após 18h
    r"carboidrato.*(?:depois|ap[oó]s|noite|jantar|18h?).*(?:engorda|veneno|vira\s+gordura)",
    r"comer\s+carboidrato.*(?:noite|ap[oó]s|depois|jantar).*(?:engorda|acumula)",
    # Pão, glúten e demonização de alimentos básicos
    r"\b(?:p[aã]o|gl[uú]ten|leite)\b.*(?:veneno|inflama\s+o\s+corpo|inflama\s+tudo)",
    r"\bgl[uú]ten\s+(?:inflama\s+qualquer\s+pessoa|faz\s+mal\s+a\s+todos|deve\s+ser\s+banido)\b",
    # Mitos sobre frutas e frutose
    r"\bfrutas?.*(?:apodrece|fermenta)\s+no\s+est[oô]mago",
    r"\bfrutose\s+d(?:as?\s+frutas?|a\s+banana|a\s+ma[cç][aã]).*(?:veneno|f[ií]gado\s+gordo|t[oó]xic)",
    # Dietas da moda restritivas e sem respaldo científico
    r"\bdieta\s+d[oa]\s+(?:ovo|sopa|lua|tipo\s+sangu[ií]neo|usp)\b.*(?:secar|emagrec|perder\s+peso)",
    # Chás detox e limpezas hepáticas milagrosas
    r"\bch[aá].*(?:detox|seca\s+barriga|elimina\s+gordura\s+do\s+f[ií]gado)",
    # Água alcalina e regulação do pH sanguíneo
    r"\b[aá]gua\s+alcalina\b.*(?:ph\s+do\s+sangue|c[aâ]ncer|cura\s+doen[cç]as)",
    # Alimentos com suposta caloria negativa
    r"\balimentos?\s+com\s+caloria\s+negativa\b",
    # Mitos de açúcares fit / mascavo que "não engordam"
    r"\b(?:a[cç][uú]car\s+mascavo|a[cç][uú]car\s+demerara|mel)\b.*(?:n[aã]o\s+engorda|caloria\s+livre)",
    # Óleo de coco milagroso
    r"\b[oó]leo\s+de\s+coco\b.*(?:queima|derrete|elimina).*(?:gordura|secar)",
]

# 2. Padrões semânticos de temas de cautela / controversos / sem individualização
PADROES_TEMA_CAUTELA = [
    # Low-carb generalizada como superior ou obrigatória para todos
    r"low[- ]?carb.*"
    r"(?:todas\s+as\s+pessoas|todo\s+mundo|sem\s+restri[cç][aã]o|melhor\s+para\s+todos)",
    r"cortar\s+carboidrato.*(?:obrigat[oó]rio|sempre|a\s+[uú]nica\s+forma)",
    # Jejum intermitente como superior absoluto ou cura universal
    r"jejum\s+intermitente.*(?:superior|cura\s+tudo|obrigat[oó]rio|sempre)",
    # Suplementação indiscriminada
    r"suplementa[cç][aã]o.*(?:indispens[aá]vel|obrigat[oó]ria|todo\s+mundo)",
    r"\b(?:creatina|whey)\b.*(?:obrigat[oó]rio|indispens[aá]vel\s+para\s+todos)",
    # Dieta cetogênica contínua sem indicação clínica
    r"\bdieta\s+cetog[eê]nica\b.*(?:para\s+qualquer\s+pessoa|sem\s+acompanhamento)",
    # Adoçantes artificiais demonizados
    r"\bado[cç]antes?\s+artificia(?:l|is)\b.*(?:veneno|causam?\s+c[aâ]ncer)",
    # Eliminação total de lipídios
    r"\b(?:gordura\s+zero|cortar\s+toda\s+gordura)\b.*(?:saud[aá]vel|ideal|necess[aá]rio)",
]

# 3. Padrões semânticos de consenso científico protetor e seguro
PADROES_CONSENSO_SEGURO = [
    # Combinação arroz e feijão
    r"arroz\s+e\s+feij[aã]o.*(?:prote[ií]na|nutriente|equil[ií]brio|amino[aá]cido)",
    # Hidratação diária adequada
    r"(?:hidrata[cç][aã]o|beber\s+[aá]gua).*(?:intestinal|reten[cç][aã]o|sa[uú]de|digest[aã]o|rins)",
    # Consumo diário de frutas e vegetais
    r"frutas?\s*(?:e\s+vegetais|e\s+verduras|e\s+legumes)?.*(?:fibras?|vitaminas?|antioxidantes?)",
    # Reeducação alimentar e flexibilidade
    r"\b(?:reeduca[cç][aã]o\s+alimentar|dieta\s+flex[ií]vel|h[aá]bitos\s+sustent[aá]veis)\b",
    # Atenção plena e mastigação
    r"\b(?:comer\s+devagar|mastiga[cç][aã]o\s+lenta|aten[cç][aã]o\s+plena\s+ao\s+comer)\b",
    # Déficit calórico moderado e sustentável
    r"\bd[eé]ficit\s+cal[oó]rico\s+moderado\b.*(?:emagrecimento|sustent[aá]vel|saud[aá]vel)",
    # Leguminosas, azeite e grãos integrais
    r"\b(?:leguminosas|gr[aã]os\s+integrais|azeite\s+de\s+oliva)\b.*(?:sa[uú]de|cardiovascular)",
]


def classificar_padrao_semantico(texto: str) -> tuple[float, str] | None:
    """Verifica se o texto casa com padrões semânticos de mito, cautela ou consenso seguro.

    Retorna tupla (risk_score, categoria) se houver casamento, ou None caso a dúvida
    não pertença a nenhum padrão pré-definido.
    """
    if not texto:
        return None
    texto_norm = texto.lower().strip()

    # 1. Mitos comprovados
    for padrao in PADROES_MITO_CONFIRMADO:
        if re.search(padrao, texto_norm):
            return SCORE_MITO, "desinformacao"

    # 2. Temas de cautela
    for padrao in PADROES_TEMA_CAUTELA:
        if re.search(padrao, texto_norm):
            return SCORE_CAUTELA, "cautela"

    # 3. Consenso seguro
    for padrao in PADROES_CONSENSO_SEGURO:
        if re.search(padrao, texto_norm):
            return SCORE_SEGURO, "seguro"

    return None


def classificar_por_fontes(fontes: list[Fonte]) -> tuple[float, str] | None:
    """Avalia o teor dos estudos científicos recuperados do Supabase pelos títulos."""
    if not fontes:
        return None

    titulos_recuperados = " ".join([f.title.lower() for f in fontes if f.title])

    termos_desinfo = [
        "desinformação",
        "infodemia",
        "terrorismo nutricional",
        "dietas da moda",
        "influenciadores",
        "magazine",
        "formulações emagrecedoras",
    ]
    termos_cautela = [
        "low-carb",
        "low carb",
        "restrição alimentar",
        "dietas restritivas",
        "transtorno alimentar",
        "suplementos",
    ]
    termos_seguro = [
        "reeducação",
        "dieta flexível",
        "habilidades sociais",
        "saúde mental",
        "comensalidade",
        "guia alimentar",
    ]

    pontos_desinfo = sum(1 for t in termos_desinfo if t in titulos_recuperados)
    pontos_cautela = sum(1 for t in termos_cautela if t in titulos_recuperados)
    pontos_seguro = sum(1 for t in termos_seguro if t in titulos_recuperados)

    if pontos_desinfo >= 2:
        return 0.72, "desinformacao"
    if pontos_cautela >= 2:
        return 0.45, "cautela"
    if pontos_seguro >= 1:
        return 0.20, "seguro"

    return None


def calcular_risco_evidencia(
    alegacao: str,
    fontes: list[Fonte],
    raw_chunks: list[dict[str, object]],
) -> tuple[float, str]:
    """Calcula o score de risco (0.0 a 1.0) e o veredito a partir de padrões e evidências do banco.

    Usado pelo fallback local e como prior de calibração no pipeline.
    """
    # 1. Padrões semânticos prioritários
    classificacao_padrao = classificar_padrao_semantico(alegacao)
    if classificacao_padrao is not None:
        return classificacao_padrao

    # 2. Avaliação a partir dos artigos no Supabase
    classificacao_fontes = classificar_por_fontes(fontes)
    if classificacao_fontes is not None:
        return classificacao_fontes

    # 3. Score cautelar padrão caso a evidência não seja conclusiva
    return SCORE_PADRAO_INCONCLUSIVO, "cautela"
