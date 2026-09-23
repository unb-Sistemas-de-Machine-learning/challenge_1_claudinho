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
    # 1. Jejum hídrico extremo / privação severa de alimentos / jejum seco / dietas extremas
    (
        r"(?:"
        r"jejum.*([3-9]|\d{2,})\s*dias|"
        r"quantos dias posso (ficar|aguentar).*"
        r"(sem comer|em jejum|tomando [aá]gua|"
        r"s[oó] no |s[oó] na |s[oó] de |apenas no |s[oó] bebendo)|"
        r"ficar\s*([3-9]|\d{2,})\s*dias.*(sem comer|s[oó] no|s[oó] de|apenas|em jejum)|"
        r"dieta\s*(l[ií]quida|do lim[aã]o|da [aá]gua).*([3-9]|\d{2,})\s*dias|"
        r"(s[oó]|apenas)\s*(no|tomando|com)\s*(suco|[aá]gua|ch[aá]|lim[aã]o).*"
        r"(secar|emagrecer|perder)\s*([3-9]|\d+)\s*kg|"
        r"(quanto tempo|quantos dias|quantas horas).{0,40}"
        r"(aguent|consigo ficar|posso ficar|d[aá] pra ficar).{0,30}"
        r"sem (comer|me alimentar|se alimentar)|"
        r"sem comer.{0,40}(emagrecer|perder \d+|secar)|"
        r"\bjejum\s+seco\b|"
        r"(?:ficar|aguentar)\s+(?:sem\s+beber\s+[aá]gua|sem\s+[aá]gua|sem\s+l[ií]quidos?)|"
        r"\b(?:respiratorianismo|viver\s+de\s+luz|dieta\s+do\s+sol)\b|"
        r"\bdieta\s+da\s+(?:t[eê]nia|solit[aá]ria)\b|"
        r"\bengolir\s+(?:t[eê]nia|solit[aá]ria|ovos?\s+de\s+verme)\b|"
        r"\bdieta\s+da\s+sonda\b"
        r")",
        "Esse jejum ou restrição extrema eu não vou calcular, porque essa prática "
        "pode te fazer mal.",
        "Compreendo a vontade de ter resultados rápidos, mas a privação severa de alimentos por "
        "múltiplos dias e, em especial, a restrição total de água (jejum seco) ou práticas "
        "biológicas extremas trazem riscos graves à saúde (como desidratação aguda, insuficiência "
        "renal fulminante, hipotensão severa, colapso metabólico, perda severa de massa magra e "
        "risco de choque). O corpo humano necessita impreterivelmente de hidratação e nutrientes "
        "constantes para manter funções vitais básicas.",
        "A ciência indica que mudanças sustentáveis e orientadas por um profissional "
        "de saúde são o caminho mais seguro e eficaz.",
    ),
    # 2. Ingestão de substâncias nocivas / tóxicas / químicas / industriais / entorpecentes
    (
        r"(?:"
        r"\bcoca[ií]na\b|\bcrack\b|\bhero[ií]na\b|\banfetamina\b|\brebite\b|\bmetanfetamina\b|"
        r"\bchumbinho\b|\bveneno\b(?! branco)|\braticida\b|[oó]leo mineral em jejum|"
        r"semente de ma[cç][aã].*c[aâ]ncer|vitamina b17|"
        r"[aá]gua oxigenada|beber desinfetante|queimador(es)? de gordura sem registro|"
        r"subst[aâ]ncia(s)? qu[ií]mica(s)?|detergente|alvejante|"
        r"\b(?:dnp|2,4-dinitrofenol|dinitrofenol)\b|"
        r"\b(?:clembuterol|pulmonil)\b|"
        r"\b(?:b[oó]rax|borato\s+de\s+s[oó]dio)\b(?=.*(tomar|beber|ingerir|desinflam|emagrec|cura))|"
        r"\b(?:mms|cds|di[oó]xido\s+de\s+cloro|clorito\s+de\s+s[oó]dio)\b|"
        r"\b(?:beber|tomar|ingerir)\s+"
        r"(?:desinfetante|detergente|sab[aã]o|querosene|gasolina|cloro|"
        r"[aá]gua\s+sanit[aá]ria|[aá]gua\s+oxigenada|soda\s+c[aá]ustica)|"
        r"\b(?:soda\s+c[aá]ustica|querosene|gasolina|t[ií]ner|acetona|am[oô]nia|[aá]gua\s+sanit[aá]ria)\b"
        r"(?=.*(beber|tomar|ingerir|emagrec|limpar|desintoxic))|"
        r"\b(?:comer|ingerir)\s+(?:terra|argila|gesso|cinzas?|giz)\b(?=.*(emagrec|desintoxic|limpar))|"
        r"\bdieta\s+do\s+algod[aã]o\b|\b(?:comer|engolir)\s+algod[aã]o\b"
        r")",
        "Essa orientação eu não posso te passar, porque essa substância pode te fazer mal.",
        "Compreendo a curiosidade e a vontade de encontrar soluções para o corpo, "
        "mas o uso de substâncias tóxicas, entorpecentes, produtos de limpeza, solventes ou "
        "compostos químicos e veterinários (como DNP, clembuterol, bórax, dióxido de cloro, "
        "óleo mineral ou drogas) traz riscos sérios à saúde (como intoxicação aguda, "
        "pneumonia lipídica, arritmias severas, falência hepática ou renal e perigo "
        "imediato à vida).",
        "A ciência indica que o cuidado com a nutrição deve ser feito sempre com base "
        "em escolhas seguras e com orientação de um profissional de saúde. Em caso de "
        "ingestão acidental ou intoxicação, procure atendimento médico imediato ou ligue "
        "para o Disque-Intoxicação da ANVISA (0800 722 6001).",
    ),
    # 3. Condutas de Transtorno Alimentar agudo / purgativas / compensatórias (Persona Camila)
    (
        r"(?:"
        r"como vomitar.*depois de comer|vomitar para emagrecer|quantos laxantes tomar para secar|"
        r"(provocar|induzir|for[cç]ar)\s+(o\s+)?v[oô]mito(?=.*(emagrec|engord|peso|secar|caloria))|"
        r"vomitar(?=.*(emagrec|engord|peso|secar|caloria))|"
        r"laxantes?(?=.*(emagrec|engord|peso|secar|barriga))|"
        r"\bdiur[eé]ticos?\b(?=.*(emagrec|perder\s+peso|secar|barriga|gordura|bater\s+peso|definir))|"
        r"(?:tomar|usar)\s+diur[eé]tico(?=.*(emagrec|peso|secar|bater\s+peso))|"
        r"\b(?:furosemida|hidroclorotiazida|espironolactona)\b"
        r"(?=.*(emagrec|peso|secar|barriga|gordura|bater\s+peso))|"
        r"\b(?:enema|clister|lavagem\s+intestinal)\b(?=.*(emagrec|secar|peso|barriga|caloria|perder))|"
        r"\benema\s+de\s+caf[eé]\b|"
        r"\bmastigar\s+e\s+cuspir\b(?=.*(comida|alimento|para\s+n[aã]o\s+engordar|caloria))|"
        r"\b(pr[oó][- ]?ana|pr[oó][- ]?mia|thinspo|bonespo)\b|"
        r"(?:comer|consumir)\s+(?:menos\s+de\s+|at[eé]\s+)?([1-4]\d{2})\s*kcal(?:\s+por\s+dia)?|"
        r"(como|dicas?\s+para)\s+(esconder|disfar[cç]ar)\s+(a\s+)?comida"
        r"(?=.*(pais|fam[ií]lia|ningu[eé]m\s+ver))|"
        r"(truques?|dicas?)\s+para\s+(enganar|aguentar)\s+(a\s+)?fome\s+(sem\s+comer|o\s+dia\s+todo)"
        r")",
        "Esse método compensatório eu não vou te ensinar, porque ele pode te fazer mal.",
        "Compreendo o sofrimento ou a culpa que podem surgir em relação à comida e ao corpo, "
        "mas métodos compensatórios, purgativos ou de restrição extrema (como vômito induzido, "
        "abuso de laxantes ou diuréticos, enemas, mastigar e cuspir comida ou dietas inferiores "
        "a 500 kcal) trazem riscos sérios à saúde (como graves desequilíbrios eletrolíticos, "
        "desgaste esofágico, arritmias e risco iminente de parada cardíaca).",
        "Se você está enfrentando dificuldades com a sua alimentação e imagem corporal, "
        "buscar acolhimento de um psicólogo, psiquiatra ou nutricionista especializado é o "
        "caminho de cuidado mais seguro e importante. Você também pode buscar apoio gratuito "
        "no Mapa da Saúde Mental (mapasaudemental.com.br) ou no CVV (ligue 188).",
    ),
    # 4. Abandono de terapia médica essencial / troca de medicação
    # (Persona Renata e condições crônicas)
    (
        r"(?:"
        r"cur(a|ar) (a )?diabetes|parar (a )?metformina|parar (a )?insulina|"
        r"substituir (o )?rem[eé]dio|"
        r"(largar|parar de tomar|abandonar|suspender|tirar|deixar de tomar)\s+"
        r"(o |a |os |as |do |da )?(rem[eé]dio|medica[cç][aã]o|medicamento|insulina|metformina)|"
        r"(largar|parar\s+de\s+tomar|abandonar|suspender|tirar|deixar\s+de\s+tomar)\s+"
        r"(o\s+|a\s+|os\s+|as\s+|do\s+|da\s+)?"
        r"(?:rem[eé]dio|medica[cç][aã]o|medicamento)\s+(?:da\s+|pra\s+|para\s+)?press[aã]o|"
        r"(curar|tratar\s+sem\s+rem[eé]dio)\s+(?:a\s+)?(hipertens[aã]o|press[aã]o\s+alta)|"
        r"(substituir|trocar)\s+(o\s+rem[eé]dio\s+da\s+press[aã]o|losartana|atenolol|anlodipino|enalapril)|"
        r"(?:parar|para|largar|larga|abandonar|abandona|substituir|substitui|suspender|suspende|"
        r"trocar|troca)\s+(?:a\s+)?(?:quimioterapia|radioterapia|quimio|radio)\b|"
        r"(?:cura|curar|tratar)\s+(?:o\s+)?c[aâ]ncer\b"
        r"(?=.*(dieta|jejum|bicarbonato|graviola|ch[aá]|alimenta|auto[- ]?fagia|substitu))|"
        r"\b(?:bicarbonato|graviola|auto[- ]?fagia)\b"
        r"(?=.*(cura|curar|tratar).*(?:c[aâ]ncer|tumor))|"
        r"(?:parar|largar|abandonar|substituir|suspender)\s+(?:a\s+)?hemodi[aá]lise|"
        r"\bcarambola\b(?=.*(renal|hemodi[aá]lise|insufici[eê]ncia))|"
        r"\b(renal|hemodi[aá]lise|insufici[eê]ncia)\b(?=.*carambola)|"
        r"(largar|parar|abandonar|substituir)\s+(?:o\s+|a\s+)?"
        r"(antidepressivo|l[ií]tio|antipsic[oó]tico|anticoagulante|varfarina|xarelto)"
        r")",
        "Essa troca de medicamento eu não vou indicar, porque ela pode te fazer mal.",
        "Compreendo a vontade de buscar opções mais naturais no dia a dia, mas nenhum "
        "alimento, chá ou prática substitui terapias farmacológicas ou o controle clínico "
        "indispensável para diabetes, hipertensão, câncer, insuficiência renal, patologias "
        "cardiovasculares ou transtornos psiquiátricos. Suspender tratamentos prescritos pode "
        "levar a descompensações graves (como cetoacidose diabética, infarto, AVC ou progressão "
        "tumoral acelerada).",
        "A ciência indica que qualquer alteração em medicações deve ser feita "
        "exclusivamente sob acompanhamento médico.",
    ),
    # 5. Riscos gestacionais / práticas abortivas / substituição de leite materno
    (
        r"(?:"
        r"\b(?:ch[aá]|erva|receita|rem[eé]dio|garrafada)\b.{0,30}"
        r"\b(?:abortar|abortivo|interromper\s+a\s+gravidez)\b|"
        r"\b(?:ch[aá]|erva|receita|rem[eé]dio|garrafada)\b.{0,30}"
        r"descer\s+(?:a\s+)?menstrua[cç][aã]o"
        r"(?=.*(gr[aá]vida|gesta[cç][aã]o|gravidez|suspeita))|"
        r"\bch[aá]\s+de\s+(?:arruda|bucha\s+paulista|poejo)\b"
        r"(?=.*(gr[aá]vida|gestante|gravidez|abort|descer))|"
        r"\b(?:jejum|ficar\s+sem\s+comer)\b.{0,25}\b(?:gr[aá]vida|na\s+gravidez|gestante)\b"
        r"(?=.*(emagrec|secar|peso|n[aã]o\s+engordar))|"
        r"(?:substituir|trocar)\s+(?:o\s+)?(?:leite\s+materno|f[oó]rmula).{0,40}"
        r"(?:por|com)\s+(?:[aá]gua\s+de\s+coco|leite\s+de\s+vaca|ch[aá]|suco)"
        r")",
        "Essa orientação durante a gestação ou para lactentes eu não posso passar, "
        "porque ela traz riscos graves a você e ao bebê.",
        "A gravidez e os primeiros meses de vida são períodos de extrema sensibilidade biológica. "
        "O uso de chás e ervas com potencial abortivo ou uterotônico (como arruda, poejo ou bucha) "
        "apresenta risco iminente de hemorragia grave, intoxicação e óbito fetal. Da mesma forma, "
        "restrições alimentares severas na gravidez comprometem o desenvolvimento do bebê, e a "
        "substituição do leite materno ou fórmula infantil em bebês menores de 6 meses por outros "
        "líquidos pode causar desnutrição aguda e desequilíbrios metabólicos graves.",
        "O acompanhamento pré-natal regular e as consultas pediátricas são indispensáveis para "
        "garantir a saúde e a segurança materna e infantil. Procure a Unidade Básica de Saúde ou "
        "seu médico de referência.",
    ),
    # 6. Automedicação com moderadores de apetite clandestinos e hormônios
    (
        r"(?:"
        r"(?:comprar|tomar|conseguir)\s+(?:sibutramina|femproporex|anfepramona|mazindol)\s+sem\s+"
        r"(?:receita|prescri[cç][aã]o)|"
        r"(?:f[oó]rmula|coquetel)\s+(?:para\s+)?emagrecer\s+com\s+(?:calmante|anfetamina|diur[eé]tico)|"
        r"\b(?:puran\s*t4|puran|levotiroxina|t3|t4)\b"
        r"(?=.*(emagrec|secar|perder\s+peso|definir))|"
        r"(?:tomar|usar)\s+(?:puran|levotiroxina|t3|t4).{0,40}"
        r"(?:emagrecer|secar|perder\s+peso)"
        r")",
        "O uso dessas substâncias ou medicamentos sem prescrição médica eu não posso indicar, "
        "porque eles podem te fazer mal.",
        "Compreendo a busca por opções para emagrecer, mas a automedicação com "
        "moderadores de apetite tarja preta, fórmulas manipuladas combinadas ou hormônios "
        "(como hormônios tireoidianos sem indicação clínica) traz riscos severos ao "
        "organismo (como taquicardia, arritmias graves, dependência química, alterações "
        "psiquiátricas agudas e elevação perigosa da pressão arterial).",
        "Tratamentos farmacológicos para controle de peso ou condições hormonais exigem "
        "diagnóstico prévio, exames laboratoriais e acompanhamento clínico rigoroso por um médico "
        "endocrinologista ou nutrólogo.",
    ),
]


def reformular_pergunta_amigavel(texto: str) -> str:
    """Reformula a dúvida do usuário em uma interrogação clara, natural e empática."""
    t = texto.strip()
    t = re.sub(r"[!?.]{2,}", "?", t)

    # Mapeamento de termos informais comuns
    regras_amigaveis = [
        # --- Emagrecimento e Gordura ---
        (
            r"\b(secar|secar a barriga|perder a barriga|definir|trincar)\b",
            "reduzir a gordura abdominal",
        ),
        (
            r"\b(perder peso|emagrecer|queimar gordura|secar 10kg|perder 10 kg)\b",
            "reduzir o peso corporal",
        ),
        (r"\b(medida|medidas|perder medida)\b", "reduzir medidas corporais"),
        # --- Inchaço e Retenção ---
        (
            r"\b(desinchar|desincha|desinche|tirar o inchaço|inchaço|retenção de líquido)\b",
            "reduzir o inchaço",
        ),
        (r"\b(desinchar a barriga|barriga inchada|estufada)\b", "reduzir a distensão abdominal"),
        (r"\b(desinflamar|inflamação|inflamado)\b", "reduzir a inflamação"),
        # --- Termos Específicos e Gírias ---
        (r"\b(shot de vinagre de ma[cç][aã]|vinagre de maçã|shot de vinagre)\b", "vinagre de maçã"),
        (r"\b(antes de uma festa|antes da festa|preparo para festa)\b", ""),
        (r"\b(detox|limpar o organismo|desintoxicar)\b", "desintoxicação"),
        (r"\b(shape|corpo perfeito|boa forma)\b", "melhora da composição corporal"),
        (r"\b(abdômen|abdomen|tanquinho)\b", "região abdominal"),
        # --- Regras Genéricas de Quantidade (Regex Dinâmico) ---
        (r"\b(perder|eliminar|queimar|secar)\s+(\d+)\s*(kg|quilos)\b", r"reduzir \2 kg"),
        # --- Alimentação e Rotina ---
        (r"\b(dieta|reeducação alimentar|mudança de hábito)\b", "plano alimentar"),
        (r"\b(jejum|jejum intermitente)\b", "jejum intermitente"),
        (r"\b(treino|exercício|atividade física|malhar)\b", "prática de exercícios físicos"),
    ]
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
