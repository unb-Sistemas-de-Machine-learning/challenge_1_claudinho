"""Resposta local para quando nenhum provedor de LLM responde.

O veredito vem do classificador de regras (`classifier.py`); este modulo so escreve o
texto, seguindo as mesmas regras do prompt v2 (APP/model/prompts.py), que por sua vez
seguem Docs/User/01, secao 2.2 (o que o Lucas espera de uma resposta):

1. o veredito vem na primeira frase;
2. linguagem de conversa;
3. a fonte fica na secao de fontes do app, nao no meio do texto (so o [Ref: ID]);
4. nenhum julgamento.

Nada aqui inventa conteudo: a explicacao so reproduz trechos que vieram da base, que e
o mesmo principio de grounding estrito do gerador com LLM.
"""

import hashlib
import re

from APP.schemas import Fonte

MODEL_VERSION = "fallback-local@classifier-v2"
TAMANHO_MAXIMO_TRECHO = 300

# Veredito na primeira frase. Tres variacoes por veredito, para a mesma resposta nao se
# repetir em todas as perguntas.
ABERTURAS = {
    "desinformacao": (
        "Isso é mito.",
        "Não é bem assim: os estudos não confirmam essa ideia.",
        "Essa ideia circula bastante, mas não se confirma.",
    ),
    "cautela": (
        "Depende.",
        "Não dá para dizer sim ou não para todo mundo.",
        "Em parte, e o detalhe faz diferença.",
    ),
    "seguro": (
        "Sim, isso é verdade.",
        "Pode confiar: isso tem respaldo.",
        "É verdade, e os estudos confirmam.",
    ),
}

# Fechamentos que servem tanto para mito do tipo "X emagrece" quanto "X faz mal". Para
# "seguro" nao ha fechamento: o risco de uma frase generica soar errada e maior que o
# ganho (ex.: "pode seguir sem culpa" depois de "acucar em excesso faz mal").
FECHAMENTOS = {
    "desinformacao": (
        "Na dúvida, desconfie de posts que prometem resultado rápido ou que culpam um "
        "alimento sozinho."
    ),
    "cautela": (
        "Como o efeito muda de pessoa para pessoa, vale conversar com um nutricionista antes "
        "de mudar a sua rotina."
    ),
}


def montar_resposta_local(
    veredito: str,
    pergunta: str,
    fontes: list[Fonte],
    trechos_por_chunk: dict[str, str],
) -> str:
    """Monta a resposta: veredito, o que um estudo registrou [Ref], e fechamento."""
    tom = veredito if veredito in ABERTURAS else "cautela"

    partes = [_escolher(ABERTURAS[tom], pergunta), _evidencia(fontes, trechos_por_chunk)]
    if tom in FECHAMENTOS:
        partes.append(FECHAMENTOS[tom])
    return " ".join(p for p in partes if p)


def _evidencia(fontes: list[Fonte], trechos: dict[str, str]) -> str:
    """Primeira fonte com trecho aproveitavel, citada so pelo ID (o titulo fica no app)."""
    for fonte in fontes:
        trecho = resumir_trecho(trechos.get(fonte.chunk_id) or fonte.excerpt)
        if trecho:
            # A referencia entra antes do ponto final: "... em si [Ref: c1]."
            corpo = trecho[:-1] if trecho.endswith(".") and not trecho.endswith("...") else trecho
            return f"Um estudo sobre o tema registrou que {corpo} [Ref: {fonte.chunk_id}]."
    return (
        "Encontramos estudos relacionados, mas os trechos não são claros o bastante para detalhar."
    )


def resumir_trecho(texto: str | None) -> str:
    """Corta o trecho em fim de frase, sem passar do limite, e ajusta o inicio.

    Os chunks sao cortados mecanicamente na ingestao e costumam comecar no meio de
    uma frase; colados crus, deixam a resposta com cara de maquina.
    """
    if not texto:
        return ""
    limpo = re.sub(r"\s+", " ", texto).strip()
    limpo = _descartar_fragmento_inicial(limpo)
    limpo = _descartar_fragmento_final(limpo)
    limpo = limpo.removesuffix("...").strip().rstrip(".").strip()

    if len(limpo) > TAMANHO_MAXIMO_TRECHO:
        corte = limpo[:TAMANHO_MAXIMO_TRECHO]
        fim_de_frase = max(corte.rfind(". "), corte.rfind("; "))
        if fim_de_frase > TAMANHO_MAXIMO_TRECHO // 3:
            limpo = corte[:fim_de_frase]
        else:
            limpo = corte[: corte.rfind(" ")].rstrip(",;:") + "..."
            return _minuscula_inicial(limpo)

    return _minuscula_inicial(limpo) + "."


def _descartar_fragmento_inicial(texto: str) -> str:
    """Pula o pedaco de frase que sobrou do corte anterior do chunk.

    Um chunk que comeca em letra minuscula ("coes avaliadas. Nao foram...") comecou
    no meio de uma frase. Se houver um fim de frase logo adiante, o texto passa a
    comecar dali; senao, fica como esta, porque cortar demais perderia o conteudo.
    """
    if not texto or not texto[0].islower():
        return texto
    fim = re.search(r"[.;!?]\s+(?=[A-ZÀ-Ú0-9])", texto)
    if fim and fim.end() < len(texto) // 2:
        return texto[fim.end() :]
    return texto


def _descartar_fragmento_final(texto: str) -> str:
    """O mesmo problema no fim: chunk que termina sem pontuacao foi cortado no meio."""
    if not texto or texto.endswith((".", "!", "?", "...")):
        return texto
    ultimo_fim = max(texto.rfind(". "), texto.rfind("! "), texto.rfind("? "))
    if ultimo_fim > len(texto) // 3:
        return texto[: ultimo_fim + 1]
    return texto


def _minuscula_inicial(texto: str) -> str:
    # "traz que Os resultados..." -> "traz que os resultados...", sem estragar siglas.
    if len(texto) > 1 and texto[0].isupper() and not texto[1].isupper():
        return texto[0].lower() + texto[1:]
    return texto


def _escolher(opcoes: tuple[str, ...], semente: str) -> str:
    """Escolha deterministica: a mesma pergunta recebe sempre a mesma frase.

    Aleatoriedade verdadeira deixaria os testes e a auditoria (trace_id) sem
    reprodutibilidade.
    """
    indice = int(hashlib.sha256(semente.encode()).hexdigest(), 16) % len(opcoes)
    return opcoes[indice]
