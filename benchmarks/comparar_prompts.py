"""Compara versoes do prompt lado a lado, com a LLM e o banco de verdade.

"Humanizado" nao se mede so com numero: este script gera um relatorio em Markdown para o
grupo LER as respostas das duas versoes para as mesmas perguntas. Junto, marca os
problemas que da para detectar automaticamente.

Uso (usa o .env: Supabase real e o provedor configurado, Ollama ou Gemini):
    uv run python -m benchmarks.comparar_prompts
    uv run python -m benchmarks.comparar_prompts --versoes rag-v1.0 rag-v2.0 --limite 5

ATENCAO: cada pergunta chama a LLM uma vez por versao e consome cota.
"""

import argparse
import re
import sys
from pathlib import Path
from statistics import mean

from APP.config import obter_settings
from APP.model import prompts
from APP.model.generator import ids_citados
from APP.model.pipeline import executar_pipeline_de_checagem
from APP.model.resposta_local import MODEL_VERSION as MODELO_FALLBACK
from APP.schemas import CheckClaimRequest
from benchmarks.avaliar_pipeline import DATASET_PADRAO, carregar_dataset

SAIDA_PADRAO = Path(__file__).parent / "comparacao_prompts.md"

MOLDE_ANTIGO = ("Entendi assim", "A ciência indica que")
VAZAMENTOS = ("fragmento", "contexto", "base de dados", "chunk", "ID_CHUNK")
ABERTURAS_CLICHE = ("Olá", "Ótima pergunta", "Compreendo", "Entendo sua")


def analisar(resposta: str, ids_recuperados: set[str]) -> dict:
    """Sinais automaticos de resposta robotica ou sem base (Docs/User/01, secao 2.2)."""
    # Mesma regra da validacao em producao: "[Ref: Ref: abc]" cita o estudo "abc".
    citados = ids_citados(resposta)
    # Os IDs dentro de [Ref: ...] costumam conter "chunk": procurar vazamento neles daria
    # alarme falso em toda resposta que cita fonte.
    sem_refs = re.sub(r"\[Ref:[^\]]*\]", "", resposta).lower()
    return {
        "palavras": len(resposta.split()),
        "comeca_com_titulo": resposta.lstrip().startswith("Resposta"),
        "molde_antigo": [m for m in MOLDE_ANTIGO if m in resposta],
        "vazamentos": [v for v in VAZAMENTOS if v.lower() in sem_refs],
        "abertura_cliche": resposta.lstrip().startswith(ABERTURAS_CLICHE),
        "refs": len(citados),
        # Citacao de estudo que o retriever nao devolveu: alucinacao (Docs/Ethics/01).
        "refs_inventadas": sorted(citados - ids_recuperados),
    }


def _veio_da_llm(resposta) -> bool:
    """Guardrail, "sem evidencia" e fallback nao dependem do prompt: ficam fora do resumo."""
    return resposta.verdict not in {"recusa_segura", "sem_evidencia"} and (
        resposta.model_version != MODELO_FALLBACK
    )


def comparar(perguntas: list[str], versoes: list[str]) -> list[dict]:
    settings = obter_settings()
    original = prompts.VERSAO_ATIVA
    resultados = []
    try:
        for pergunta in perguntas:
            linha = {"pergunta": pergunta, "versoes": {}}
            for versao in versoes:
                prompts.VERSAO_ATIVA = versao
                resposta = executar_pipeline_de_checagem(
                    CheckClaimRequest(input_type="text", text=pergunta), settings, 0, "comparacao"
                )
                ids = {f.chunk_id for f in resposta.sources}
                linha["versoes"][versao] = {
                    "answer": resposta.answer,
                    "verdict": resposta.verdict,
                    "modelo": resposta.model_version,
                    "usou_llm": _veio_da_llm(resposta),
                    **analisar(resposta.answer, ids),
                }
            resultados.append(linha)
    finally:
        prompts.VERSAO_ATIVA = original
    return resultados


def _resumo(resultados: list[dict], versao: str) -> dict:
    itens = [r["versoes"][versao] for r in resultados if r["versoes"][versao]["usou_llm"]]
    if not itens:
        return {"respostas_da_llm": 0}
    return {
        "respostas_da_llm": len(itens),
        "palavras_media": round(mean(i["palavras"] for i in itens)),
        "com_titulo": sum(i["comeca_com_titulo"] for i in itens),
        "com_molde_antigo": sum(bool(i["molde_antigo"]) for i in itens),
        "com_vazamento": sum(bool(i["vazamentos"]) for i in itens),
        "abertura_cliche": sum(i["abertura_cliche"] for i in itens),
        "refs_inventadas": sum(len(i["refs_inventadas"]) for i in itens),
    }


def gerar_relatorio(resultados: list[dict], versoes: list[str]) -> str:
    linhas = ["# Comparação de prompts", ""]
    linhas += [
        "Respostas que não passaram pela LLM (guardrail, sem evidência ou fallback) ficam "
        "fora do resumo, porque não dependem do prompt.",
        "",
        "## Resumo",
        "",
        "| Métrica | " + " | ".join(versoes) + " |",
        "|---|" + "---|" * len(versoes),
    ]
    resumos = {v: _resumo(resultados, v) for v in versoes}
    for chave in (
        "respostas_da_llm",
        "palavras_media",
        "com_titulo",
        "com_molde_antigo",
        "com_vazamento",
        "abertura_cliche",
        "refs_inventadas",
    ):
        valores = [str(resumos[v].get(chave, "-")) for v in versoes]
        linhas.append(f"| {chave} | " + " | ".join(valores) + " |")

    linhas += ["", "## Respostas", ""]
    for r in resultados:
        linhas += [f"### {r['pergunta']}", ""]
        for versao in versoes:
            item = r["versoes"][versao]
            origem = "LLM" if item["usou_llm"] else f"sem LLM ({item['modelo']})"
            alertas = [
                *(f"molde antigo: {m}" for m in item["molde_antigo"]),
                *(f"vazou: {v}" for v in item["vazamentos"]),
                *(f"ref inventada: {x}" for x in item["refs_inventadas"]),
            ]
            linhas.append(
                f"**{versao}** · {item['verdict']} · {item['palavras']} palavras · {origem}"
            )
            if alertas:
                linhas.append(f"> ⚠️ {'; '.join(alertas)}")
            linhas += ["", item["answer"], ""]
        linhas += ["---", ""]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--versoes", nargs="+", default=list(prompts.VERSOES))
    parser.add_argument("--limite", type=int, help="usa so as N primeiras perguntas")
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args(argv)

    desconhecidas = set(args.versoes) - set(prompts.VERSOES)
    if desconhecidas:
        print(f"Versoes desconhecidas: {desconhecidas}. Disponiveis: {list(prompts.VERSOES)}")
        return 2

    perguntas = [item["entrada"] for item in carregar_dataset(DATASET_PADRAO)]
    if args.limite:
        perguntas = perguntas[: args.limite]

    resultados = comparar(perguntas, args.versoes)
    args.saida.write_text(gerar_relatorio(resultados, args.versoes), encoding="utf-8")

    usaram_llm = sum(1 for r in resultados for v in r["versoes"].values() if v["usou_llm"])
    print(f"Relatorio: {args.saida}")
    if not usaram_llm:
        print("AVISO: nenhuma resposta veio da LLM. Confira o provedor no .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
