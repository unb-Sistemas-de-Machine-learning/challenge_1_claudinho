"""Classificador de Risco e Veredito baseado nas Evidências do Supabase.

Baseado em:
- Docs/Model/01_metricas_e_avaliacao.md (Limiares de decisão e matriz de custos)
- Docs/Model/03_processamento_linguagem_internet.md (Sinais semânticos de mitos)
- Docs/Data/02_armazenamento_e_estrutura.md (Classificação por evidência científica)
"""

import re

from APP.schemas import Fonte

# Padrões semanticos de mitos, cautela e consenso científico
PADROES_MITO_CONFIRMADO = [
    r"(queima|queimar) gordura.*(lim[aã]o|jejum|vinagre)",
    r"(lim[aã]o|vinagre).*(queima|desincha|desinflama|secar)",
    r"carboidrato.*(depois|ap[oó]s|noite).*18h.*(engorda|veneno)",
    r"(p[aã]o|arroz|fruta).*(veneno|inflama o corpo|apodrece)",
    r"dieta do ovo.*secar",
    r"ch[aá].*(detox|elimina gordura do f[ií]gado)",
    r"[aá]gua alcalina.*(ph do sangue|c[aâ]ncer)",
]

PADROES_TEMA_CAUTELA = [
    r"low[- ]?carb.*(todas as pessoas|todo mundo|sem restri[cç][aã]o)",
    r"cortar carboidrato.*(obrigat[oó]rio|sempre)",
    r"jejum intermitente.*(superior|cura|sempre)",
    r"suplementa[cç][aã]o.*(indispens[aá]vel|todo mundo)",
]

PADROES_CONSENSO_SEGURO = [
    r"arroz e feij[aã]o.*(prote[ií]na|nutriente|equil[ií]brio)",
    r"hidrata[cç][aã]o.*(intestinal|reten[cç][aã]o|sa[uú]de)",
    r"frutas.*(fibras|vitaminas|antioxidantes)",
    r"reeduca[cç][aã]o alimentar|dieta flex[ií]vel",
    r"comer devagar|mastiga[cç][aã]o lenta",
]


def calcular_risco_evidencia(
    alegacao: str,
    fontes: list[Fonte],
    raw_chunks: list[dict[str, object]],
) -> tuple[float, str]:
    """Calcula o score de risco (0.0 a 1.0) e o veredito a partir das evidências do banco."""
    texto_norm = alegacao.lower().strip()

    # Checagem de mitos
    for padrao in PADROES_MITO_CONFIRMADO:
        if re.search(padrao, texto_norm):
            return 0.78, "desinformacao"

    # Checagem de temas de cautela
    for padrao in PADROES_TEMA_CAUTELA:
        if re.search(padrao, texto_norm):
            return 0.48, "cautela"

    # Checagem de consenso científico
    for padrao in PADROES_CONSENSO_SEGURO:
        if re.search(padrao, texto_norm):
            return 0.18, "seguro"

    # Avaliação a partir dos artigos no Supabase
    if fontes:
        titulos_recuperados = " ".join([f.title.lower() for f in fontes])

        termos_desinfo = [
            "desinformação",
            "infodemia",
            "terrorismo nutricional",
            "dietas da moda",
            "influenciadores",
            "magazine",
        ]
        termos_cautela = [
            "low-carb",
            "low carb",
            "restrição alimentar",
            "transtorno alimentar",
            "suplementos",
        ]
        termos_seguro = [
            "reeducação",
            "dieta flexível",
            "habilidades sociais",
            "saúde mental",
            "comensalidade",
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

    # Score cautelar caso evidência não seja conclusiva
    return 0.38, "cautela"
