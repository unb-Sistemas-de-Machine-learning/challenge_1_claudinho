"""Módulo de Normalização, Extração de Claims e Guardrails Pre-Retrieval.

Documentado em:
- Docs/Model/03_processamento_linguagem_internet.md (Few-Shot e termos)
- Docs/Ethics/01_seguranca_e_anti_alucinacao.md (Safe Refusal Policy)
- Docs/Ethics/02_grupos_de_risco_e_filtros.md (Protecao de grupos vulneraveis)
"""

import re

MAPA_TERMOS_POPULARES = {
    r"\bsecar (a )?barriga\b": "perda de gordura abdominal",
    r"\bqueimar gordura\b": "lipólise e oxidação de ácidos graxos",
    r"\bdesinchar( o corpo)?\b": "redução de retenção hídrica corporal",
    r"\bveneno branco\b": "açúcar refinado ou sal de cozinha",
    r"\breset metab[oó]lico\b": "aumento da taxa metabólica basal",
    r"\bshot de vinagre\b": "ingestão de ácido acético em jejum",
    r"\bágua com gratid[aã]o\b": "água fluidificada sem alteração química",
    r"\binflamar o corpo\b": "indução de marcadores inflamatórios sistêmicos",
    r"\bchutar o balde\b": "episódio de hiperfagia alimentar sem planejamento",
}

# Padrões de risco crítico (Docs/Ethics/01 e Docs/Ethics/02)
PADROES_RISCO_CRITICO = [
    # Jejum hídrico extremo / privação severa de alimentos / dietas líquidas
    (
        r"(jejum.*([3-9]|\d{2,})\s*dias|"
        r"quantos dias posso (ficar|aguentar).*"
        r"(sem comer|em jejum|tomando [aá]gua|s[oó] no |s[oó] na |"
        r"s[oó] de |apenas no |s[oó] bebendo)|"
        r"ficar\s*([3-9]|\d{2,})\s*dias.*(sem comer|s[oó] no|s[oó] de|apenas|em jejum)|"
        r"dieta\s*(l[ií]quida|do lim[aã]o|da [aá]gua).*([3-9]|\d{2,})\s*dias|"
        r"(s[oó]|apenas)\s*(no|tomando|com)\s*(suco|[aá]gua|ch[aá]|lim[aã]o).*(secar|emagrecer|perder)\s*([3-9]|\d+)\s*kg|"
        # Duracao da privacao perguntada sem numero ("quanto tempo aguento sem comer").
        r"(quanto tempo|quantos dias|quantas horas).{0,40}"
        r"(aguent|consigo ficar|posso ficar|d[aá] pra ficar).{0,30}"
        r"sem (comer|me alimentar|se alimentar)|"
        r"sem comer.{0,40}(emagrecer|perder \d+|secar))",
        "Esse jejum eu não vou calcular, porque ele pode te fazer mal.",
        "Compreendo a vontade de ter resultados rápidos, mas práticas como restrições "
        "extremas ou uso de substâncias sem indicação trazem riscos sérios à saúde "
        "(como fraqueza, deficiências nutricionais e alterações metabólicas).",
        "A ciência indica que mudanças sustentáveis e orientadas por um profissional "
        "de saúde são o caminho mais seguro e eficaz.",
    ),
    # Ingestão de substâncias nocivas / tóxicas / entorpecentes
    (
        # \b em cada termo: sem ele, "crack" casa dentro de "cream cracker" e "veneno"
        # dentro de "veneno branco", que e giria para acucar e deve virar checagem normal.
        r"(\bcoca[ií]na\b|\bcrack\b|\bhero[ií]na\b|\banfetamina\b|\brebite\b|"
        r"\bmetanfetamina\b|\bchumbinho\b|"
        r"\bveneno\b(?! branco)|\braticida\b|[oó]leo mineral em jejum|"
        r"semente de ma[cç][aã].*c[aâ]ncer|vitamina b17|"
        r"[aá]gua oxigenada|beber desinfetante|queimador(es)? de gordura sem registro|"
        r"subst[aâ]ncia(s)? qu[ií]mica(s)?|detergente|alvejante)",
        "Essa orientação eu não posso te passar, porque essa substância pode te fazer mal.",
        "Compreendo a curiosidade e a vontade de encontrar soluções para o corpo, "
        "mas o uso de substâncias tóxicas, entorpecentes ou não alimentares (como óleo mineral, "
        "drogas ou compostos químicos) traz riscos sérios à saúde (como intoxicação aguda, "
        "pneumonia lipídica, arritmias e perigo imediato à vida).",
        "A ciência indica que o cuidado com a nutrição deve ser feito sempre com base "
        "em escolhas seguras e com orientação de um profissional de saúde.",
    ),
    # Condutas de Transtorno Alimentar agudo / purgativas (Persona Camila)
    (
        r"(como vomitar.*depois de comer|vomitar para emagrecer|quantos laxantes tomar para secar|"
        # Vomito e laxante so contam com intencao de peso: "e normal vomitar depois de
        # comer muito?" e duvida de sintoma e nao pode cair na recusa.
        r"(provocar|induzir|for[cç]ar)\s+(o\s+)?v[oô]mito(?=.*(emagrec|engord|peso|secar|caloria))|"
        r"vomitar(?=.*(emagrec|engord|peso|secar|caloria))|"
        r"laxantes?(?=.*(emagrec|engord|peso|secar|barriga)))",
        "Esse método compensatório eu não vou te ensinar, porque ele pode te fazer mal.",
        "Compreendo o sofrimento ou a culpa que podem surgir em relação à comida e ao corpo, "
        "mas métodos compensatórios e purgativos (como vômito induzido ou abuso de laxantes) "
        "trazem riscos sérios à saúde (como graves desequilíbrios eletrolíticos, desgaste "
        "esofágico e risco iminente de parada cardíaca).",
        "Se você está enfrentando dificuldades com a sua alimentação e imagem corporal, "
        "buscar acolhimento de um psicólogo, psiquiatra ou nutricionista especializado é o "
        "caminho de cuidado mais seguro e importante.",
    ),
    # Abandono de terapia médica essencial (Persona Renata)
    (
        r"(cur(a|ar) (a )?diabetes|parar (a )?metformina|parar (a )?insulina|"
        r"substituir (o )?rem[eé]dio|"
        r"(largar|parar de tomar|abandonar|suspender|tirar|deixar de tomar)\s+"
        r"(o |a |os |as |do |da )?(rem[eé]dio|medica[cç][aã]o|medicamento|insulina|metformina))",
        "Essa troca de medicamento eu não vou indicar, porque ela pode te fazer mal.",
        "Compreendo a vontade de buscar opções mais naturais no dia a dia, mas nenhum "
        "alimento, chá ou prática substitui terapias farmacológicas ou o controle clínico "
        "para diabetes e outras condições crônicas.",
        "A ciência indica que qualquer alteração em medicações deve ser feita "
        "exclusivamente sob acompanhamento médico.",
    ),
]


# Mapeamento de termos informais de saúde para termos científicos e empáticos
REGRAS_AMIGAVEIS: list[tuple[str, str]] = [
    # --- 1. Regras Dinâmicas de Quantidade e Metas ---
    (
        r"\b(perder|eliminar|queimar|secar|baixar)\s+(\d+(?:[.,]\d+)?)\s*"
        r"(?:kg|quilos?|kilos?)\s+(?:r[aá]pido|rapidamente|urgente|em\s+poucos\s+dias)\b",
        r"reduzir \2 kg rapidamente",
    ),
    (
        r"\b(perder|eliminar|queimar|secar|baixar)\s+(\d+(?:[.,]\d+)?)\s*(?:kg|quilos?|kilos?)\b",
        r"reduzir \2 kg",
    ),
    (
        r"\b(\d+(?:[.,]\d+)?)\s*(?:kg|quilos?|kilos?)\s+a\s+menos\b",
        r"redução de \1 kg",
    ),
    (
        r"\b(perder|eliminar|reduzir|baixar)\s+(\d+(?:[.,]\d+)?)\s*(?:cm|cent[ií]metros?)"
        r"(?:\s+de\s+(?:cintura|barriga|medidas?))?\b",
        r"reduzir \2 cm de medidas corporais",
    ),
    (r"\b(?:perder|baixar|diminuir|eliminar)\s+medidas?\b", "reduzir medidas corporais"),
    (r"\bperda\s+de\s+medidas?\b", "redução de medidas corporais"),

    # --- 2. Bebidas Funcionais, Shots, Sucos e Detox ---
    (r"\bch[aá]s?\s+seca[- ]barriga\b", "chá para redução de gordura abdominal"),
    (r"\bch[aá]s?\s+emagrecedor(?:es)?\b", "chá para auxílio no emagrecimento"),
    (r"\bch[aá]s?\s+(?:desincha|para\s+desinchar)\b", "chá com ação diurética"),
    (
        r"\b(?:tomar|beber|ingerir|consumir)\s+shot\s+de\s+vinagre(?:\s+de\s+ma[cç][aã])?\b",
        "tomar vinagre de maçã",
    ),
    (r"\bshot\s+de\s+vinagre(?:\s+de\s+ma[cç][aã])?\b", "consumo de vinagre de maçã"),
    (
        r"\b(?:tomar|beber|ingerir|consumir)\s+shot\s+"
        r"(?:matinal|da\s+imunidade|de\s+lim[aã]o|de\s+c[uú]rcuma)\b",
        "consumir bebida matinal funcional",
    ),
    (
        r"\bshot\s+(?:matinal|da\s+imunidade|de\s+lim[aã]o|de\s+c[uú]rcuma)\b",
        "bebida matinal funcional",
    ),
    (r"\b(?:suco|bebida)\s+detox\b", "suco de frutas e vegetais"),
    (r"\bdieta\s+detox\b", "plano alimentar baseado em alimentos naturais"),
    (
        r"\b(?:limpar|desintoxicar)\s+o\s+(?:organismo|f[ií]gado|corpo)\b",
        "eliminação natural de toxinas pelo fígado",
    ),
    (
        r"\b(?:limpa|desintoxica)\s+o\s+(?:organismo|f[ií]gado|corpo)\b",
        "elimina toxinas do organismo",
    ),
    (
        r"\b(?:limpam|desintoxicam)\s+o\s+(?:organismo|f[ií]gado|corpo)\b",
        "eliminam toxinas do organismo",
    ),
    (r"\b(?:eliminar|expulsar|varrer)\s+toxinas\b", "eliminar toxinas do organismo"),
    (r"\bdetox\b", "desintoxicação"),

    # --- 3. Gordura Abdominal, Cintura e Gordura Localizada ---
    (r"\bch[aá]\s+para\s+secar\s+(?:a\s+)?barriga\b", "chá para redução de gordura abdominal"),
    (
        r"\b(?:secar|perder|queimar|eliminar|diminuir|tirar|sumir\s+com)\s+(?:a\s+)?barriga\b",
        "reduzir a gordura abdominal",
    ),
    (
        r"\b(?:seca|perde|queima|elimina|diminui|tira)\s+(?:a\s+)?barriga\b",
        "reduz a gordura abdominal",
    ),
    (
        r"\b(?:secam|perdem|queimam|eliminam|diminuem|tiram)\s+(?:a\s+)?barriga\b",
        "reduzem a gordura abdominal",
    ),
    (r"\bgordura\s+(?:da\s+barriga|abdominal)\b", "gordura abdominal"),
    (r"\bbarriga\s+(?:chapada|negativa)\b", "redução da gordura abdominal"),
    (r"\b(?:barriga|abd[oô]men?)\s+de\s+tanquinho\b", "definição da musculatura abdominal"),
    (r"\btanquinho\b", "definição muscular abdominal"),
    (
        r"\b(?:trincar|definir)\s+(?:o\s+abd[oô]men?|a\s+barriga)\b",
        "promover definição muscular abdominal",
    ),
    (
        r"\b(?:trinca|define)\s+(?:o\s+abd[oô]men?|a\s+barriga)\b",
        "promove definição muscular abdominal",
    ),
    (
        r"\b(?:trincam|definem)\s+(?:o\s+abd[oô]men?|a\s+barriga)\b",
        "promovem definição muscular abdominal",
    ),
    (r"\b(?:pochete|culotes?|pneuzinhos?|dobrinhas?)\b", "gordura localizada"),
    (r"\bgordurinhas?\s+localizadas?\b", "gordura localizada"),
    (r"\bbanha\b", "gordura corporal"),

    # --- 4. Inchaço, Retenção Hídrica, Distensão Abdominal e Inflamação ---
    (r"\bbarriga\s+(?:estufada\s+e\s+inchada|inchada\s+e\s+estufada)\b", "distensão abdominal"),
    (r"\bdesinchar\s+(?:a\s+)?barriga\b", "reduzir a distensão abdominal"),
    (r"\bdesincha\s+(?:a\s+)?barriga\b", "reduz a distensão abdominal"),
    (r"\bdesincham\s+(?:a\s+)?barriga\b", "reduzem a distensão abdominal"),
    (r"\bbarriga\s+(?:inchada|estufada)\b", "distensão abdominal"),
    (
        r"\b(?:sensa[cç][aã]o\s+de\s+)?estufamento(?:\s+abdominal|\s+na\s+barriga)?\b",
        "distensão abdominal",
    ),
    (
        r"\b(?:tirar|eliminar|diminuir|combater)\s+(?:a\s+)?reten[cç][aã]o\s+de\s+l[ií]quidos?\b",
        "reduzir a retenção hídrica",
    ),
    (
        r"\b(?:tira|elimina|diminui|combate)\s+(?:a\s+)?reten[cç][aã]o\s+de\s+l[ií]quidos?\b",
        "reduz a retenção hídrica",
    ),
    (r"\b(?:tirar|eliminar|combater|acabar\s+com)\s+o\s+incha[cç]o\b", "reduzir o inchaço"),
    (r"\b(?:tira|elimina|combate|acaba\s+com)\s+o\s+incha[cç]o\b", "reduz o inchaço"),
    (r"\bdesinchar(?:\s+o\s+corpo)?\b", "reduzir o inchaço"),
    (r"\bdesincha(?:\s+o\s+corpo)?\b", "reduz o inchaço"),
    (r"\bdesincham(?:\s+o\s+corpo)?\b", "reduzem o inchaço"),
    (r"\breten[cç][aã]o\s+de\s+l[ií]quidos?\b", "retenção hídrica"),
    (r"\b(?:corpo\s+retido|l[ií]quido\s+retido)\b", "retenção hídrica"),
    (r"\bdesinflamar(?:\s+o\s+(?:corpo|organismo))?\b", "reduzir a inflamação"),
    (r"\bdesinflama(?:\s+o\s+(?:corpo|organismo))?\b", "reduz a inflamação"),
    (r"\bdesinflamam(?:\s+o\s+(?:corpo|organismo))?\b", "reduzem a inflamação"),
    (r"\binflamar\s+o\s+(?:corpo|organismo)\b", "provocar inflamação corporal"),
    (r"\binflama\s+o\s+(?:corpo|organismo)\b", "provoca inflamação corporal"),
    (r"\bcorpo\s+inflamado\b", "quadro inflamatório"),

    # --- 5. Gordura Corporal, Queima e Perda de Peso ---
    (
        r"\b(?:queimar|derreter|torrar|eliminar)\s+gordura(?:\s+corporal)?\b",
        "reduzir a gordura corporal",
    ),
    (
        r"\b(?:queima|derrete|torra|elimina)\s+gordura(?:\s+corporal)?\b",
        "reduz a gordura corporal",
    ),
    (
        r"\b(?:queimam|derretem|torram|eliminam)\s+gordura(?:\s+corporal)?\b",
        "reduzem a gordura corporal",
    ),
    (r"\bqueima\s+de\s+gordura\b", "oxidação de gordura corporal"),
    (
        r"\b(?:perder\s+peso|emagrecer|secar)\s+(?:r[aá]pido|rapidamente|urgente|em\s+poucos\s+dias)\b",
        "reduzir o peso rapidamente",
    ),
    (r"\b(?:perder\s+peso|emagrecer|secar)\s+de\s+vez\b", "reduzir o peso de forma definitiva"),
    (r"\bemagrecimento\s+r[aá]pido\b", "perda de peso rápida"),
    (r"\bperder\s+peso\b", "reduzir o peso corporal"),
    (r"\bperde\s+peso\b", "reduz o peso corporal"),
    (r"\bperdem\s+peso\b", "reduzem o peso corporal"),
    (r"\bemagrecer\b", "reduzir o peso corporal"),
    (r"\bemagrece\b", "reduz o peso corporal"),
    (r"\bemagrecem\b", "reduzem o peso corporal"),
    (r"\b(?:dar\s+uma\s+secada|secar)\b", "reduzir o percentual de gordura"),
    (r"\b(?:trincar|definir)\b", "melhorar a definição muscular"),
    (
        r"\b(?:meter\s+o\s+shape|shape|corpo\s+perfeito|boa\s+forma)\b",
        "melhora da composição corporal",
    ),

    # --- 6. Mitos Nutricionais e Conceitos Distorcidos ---
    (
        r"\b(?:[eé]|s[aã]o|seria|considerad[oa])\s+(?:um\s+|o\s+)?veneno\s+branco\b",
        "é prejudicial à saúde",
    ),
    (r"\bveneno\s+branco\b", "açúcar refinado ou sal"),
    (
        r"\b(?:acelerar|turbinar|ativar)\s+o\s+metabolismo\s+(?:lento|pregui[cç]oso|travado)\b",
        "aumentar a taxa metabólica",
    ),
    (r"\b(?:acelerar|turbinar|ativar)\s+o\s+metabolismo\b", "aumentar a taxa metabólica basal"),
    (r"\b(?:acelera|turbina|ativa)\s+o\s+metabolismo\b", "aumenta a taxa metabólica basal"),
    (r"\b(?:aceleram|turbinam|ativam)\s+o\s+metabolismo\b", "aumentam a taxa metabólica basal"),
    (r"\bmetabolismo\s+(?:lento|pregui[cç]oso|travado)\b", "taxa metabólica reduzida"),
    (r"\b(?:reset|resetar|reiniciar)\s+metab[oó]lico\b", "estímulo à taxa metabólica basal"),
    (r"\b[aá]gua\s+com\s+gratid[aã]o\b", "água sem propriedades terapêuticas"),
    (r"\b[aá]gua\s+(?:fluidificada|magnetizada)\b", "água sem propriedades terapêuticas"),
    (r"\bqueimar\s+calorias?\b", "aumentar o gasto calórico"),
    (r"\bqueima\s+calorias?\b", "aumenta o gasto calórico"),
    (r"\bqueimam\s+calorias?\b", "aumentam o gasto calórico"),

    # --- 7. Hábitos Alimentares, Restrições e Comportamento ---
    (r"\bantes\s+de\s+(?:uma\s+|da\s+)?festa\b", "antes de um evento"),
    (
        r"\b(?:chutar\s+o\s+balde|enfiar\s+o\s+p[eé]\s+na\s+jaca)\b",
        "exagerar no consumo alimentar",
    ),
    (
        r"\b(?:chutei\s+o\s+balde|enfiei\s+o\s+p[eé]\s+na\s+jaca)\b",
        "exagerei no consumo alimentar",
    ),
    (r"\bdia\s+do\s+lixo\b", "dia de refeição livre"),
    (r"\brefei[cç][aã]o\s+(?:do\s+)?lixo\b", "refeição livre"),
    (
        r"\b(?:furar\s+a\s+dieta|sair\s+da\s+dieta|burlar\s+a\s+dieta)\b",
        "desviar do planejamento alimentar",
    ),
    (
        r"\b(?:zerar|cortar)\s+(?:os?\s+)?carbo(?:idrato)?s?\s+(?:ap[oó]s|depois\s+das|[aà]s)\s*18h?\b",
        "restringir carboidratos no período noturno",
    ),
    (
        r"\b(?:comer|consumir|ingerir)\s+carbo(?:idrato)?s?\s+(?:ap[oó]s|depois\s+das|[aà]s)\s*18h?\b",
        "consumir carboidratos no período noturno",
    ),
    (
        r"\bcarbo(?:idrato)?s?\s+(?:ap[oó]s|depois\s+das|[aà]s)\s*18h?\b",
        "carboidratos no período noturno",
    ),
    (r"\bcarbo(?:idrato)?s?\s+[aà]\s+noite\b", "carboidratos no período noturno"),
    (
        r"\b(?:zerar|cortar(?:\s+de\s+vez)?)\s+(?:os?\s+)?carbo(?:idrato)?s?\b",
        "restringir severamente os carboidratos",
    ),
    (
        r"\b(?:zerar|cortar(?:\s+de\s+vez)?)\s+(?:o\s+)?a[cç][uú]car\b",
        "restringir o consumo de açúcar",
    ),
    (r"\bcortar\s+(?:o\s+)?gl[uú]ten\b", "eliminar o glúten da dieta"),
    (r"\bcarbos?\b", "carboidratos"),
    (r"\b(?:comer\s+besteiras?|comer\s+porcarias?)\b", "consumir alimentos ultraprocessados"),
    (r"\bcalorias?\s+vazias?\b", "calorias de baixa densidade nutricional"),
    (r"\balimentos?\s+que\s+engorda(?:m)?\b", "alimentos de alta densidade calórica"),
    (r"\balimentos?\s+que\s+emagrece(?:m)?\b", "alimentos de baixa densidade calórica"),
    (r"\bengorda\s+muito\b", "favorece muito o ganho de peso"),
    (r"\bengordam\s+muito\b", "favorecem muito o ganho de peso"),
    (r"\bengorda\s+mais\b", "favorece mais o ganho de peso"),
    (r"\bengordam\s+mais\b", "favorecem mais o ganho de peso"),
    (r"\bengorda\b", "favorece o ganho de peso"),
    (r"\bengordam\b", "favorecem o ganho de peso"),
    (r"\bcomida\s+de\s+verdade\b", "alimentos in natura"),

    # --- 8. Exercícios e Treino ---
    (r"\b(?:malhar|puxar\s+ferro)\b", "praticar musculação"),
    (r"\b(?:cardio|aer[oó]bico)\s+em\s+jejum\b", "exercício aeróbico em jejum"),
    (
        r"\b(?:ganhar|construir|crescer)\s+(?:m[uú]sculos?|massa\s+muscular)\b",
        "promover hipertrofia muscular",
    ),

    # --- 9. Ceticismo, Mitos e Promessas Milagrosas ---
    (r"\b(?:ou\s+)?(?:[eé]\s+)?meme\b", "ou é um mito"),
    (
        r"\b(?:[eé]\s+)?(?:fake\s+news|fake|balela|conversa\s+fiada)\b",
        "é um mito sem base científica",
    ),
    (
        r"\b(?:receita|m[eé]todo|f[oó]rmula|rem[eé]dio|solu[cç][aã]o)\s+milagros[oa]\b",
        "método sem respaldo científico",
    ),
    (
        r"\brem[eé]dio\s+caseiro\s+para\s+(?:emagrecer|secar|perder\s+peso|perder\s+barriga)\b",
        "preparado caseiro para perda de peso",
    ),
]


def reformular_pergunta_amigavel(texto: str) -> str:
    """Reformula a dúvida do usuário em uma interrogação clara, natural e empática."""
    t = texto.strip()
    t = re.sub(r"[!?.]{2,}", "?", t)

    regras_amigaveis = REGRAS_AMIGAVEIS
    for p, r in regras_amigaveis:
        t = re.sub(p, r, t, flags=re.IGNORECASE)

    t = " ".join(t.split())
    if not t.endswith("?"):
        t = f"{t}?"

    if len(t) > 1:
        t = t[0].upper() + t[1:]
    return t


def checar_recusa_segura(
    texto: str,
    pergunta_amigavel: str | None = None,
) -> tuple[bool, str]:
    """Avalia se o texto aciona um guardrail ético e formata a Resposta de Cuidado."""
    texto_norm = texto.lower().strip()
    pergunta = pergunta_amigavel or reformular_pergunta_amigavel(texto)

    for padrao, abertura, justificativa, orientacao in PADROES_RISCO_CRITICO:
        if re.search(padrao, texto_norm):
            resposta_humana = (
                f"Resposta de cuidado\n"
                f"{abertura}\n"
                f"Entendi assim: {pergunta}\n\n"
                f"{justificativa}\n\n"
                f"{orientacao}"
            )
            return True, resposta_humana

    return False, ""


def normalizar_alegacao_heuristica(texto: str) -> str:
    """Normaliza o texto do usuário substituindo girias nutricionais por termos científicos.

    Utilizado como baseline ou fallback quando nao houver LLM extrator conectado.
    """
    normalizado = texto.strip()
    normalizado = re.sub(r"[kK]{3,}", "", normalizado)
    normalizado = re.sub(r"[!?.]{2,}", "?", normalizado)

    for padrao, substituto in MAPA_TERMOS_POPULARES.items():
        normalizado = re.sub(padrao, substituto, normalizado, flags=re.IGNORECASE)

    normalizado = " ".join(normalizado.split())

    # Assegura formato interrogativo caso dúvida
    if not normalizado.endswith("?"):
        normalizado = f"{normalizado}?"

    return normalizado
