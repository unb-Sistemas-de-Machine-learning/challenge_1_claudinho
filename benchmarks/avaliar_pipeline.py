"""Avaliacao offline do pipeline: F2, Recall, recusa segura e latencia.

Baseado em Docs/Model/01_metricas_e_avaliacao.md e Docs/Ethics/01.

Uso:
    uv run python -m benchmarks.avaliar_pipeline
    uv run python -m benchmarks.avaliar_pipeline --min-recall 0.95 --min-f2 0.90
    uv run python -m benchmarks.avaliar_pipeline --url https://api... --token <JWT>

Codigo de saida: 0 se as metas passadas foram atingidas, 1 se alguma falhou,
2 se houve requisicoes sem resposta. E o que permite usar este script como
quality gate no CI (Docs/Production/01, secao 3.2).
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from benchmarks._cliente import cabecalho, criar_cliente
from benchmarks.metricas import Caso, calcular

DATASET_PADRAO = Path(__file__).parent / "dataset_benchmark.json"
ROTA = "/api/v1/check-claim"

# Com um unico token (JWT real), a API permite 10 checagens por minuto por usuario.
INTERVALO_COM_TOKEN_UNICO_S = 6.5


def carregar_dataset(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


async def executar(
    dataset: list[dict],
    url: str | None = None,
    token: str | None = None,
    intervalo_s: float | None = None,
    repeticoes: int = 1,
) -> list[Caso]:
    """Roda cada caso do dataset contra a API e devolve os resultados brutos.

    Sem `--token`, cada caso usa uma identidade propria (valido em APP_ENV=local).
    Antes, todos os casos usavam o mesmo token: a partir do 11o caso a API devolvia
    429 e o script quebrava ao imprimir um veredito inexistente.
    """
    if intervalo_s is None:
        intervalo_s = INTERVALO_COM_TOKEN_UNICO_S if token else 0.0

    # A LLM nao responde sempre igual: repetir e somar reduz o peso da sorte na comparacao.
    rodadas = [
        {**item, "id": f"{item['id']}#{r + 1}"} if repeticoes > 1 else item
        for r in range(repeticoes)
        for item in dataset
    ]

    casos: list[Caso] = []
    async with criar_cliente(url) as cliente:
        for indice, item in enumerate(rodadas):
            if indice and intervalo_s:
                await asyncio.sleep(intervalo_s)

            identidade = token or f"benchmark-{item['id']}"
            inicio = time.perf_counter()
            resposta = await cliente.post(
                ROTA,
                headers=cabecalho(identidade),
                json={"input_type": "text", "text": item["entrada"]},
            )
            parede_ms = (time.perf_counter() - inicio) * 1000

            corpo = resposta.json() if resposta.status_code == 200 else {}
            casos.append(
                Caso(
                    id=item["id"],
                    tipo=item["tipo"],
                    esperado=item["veredito_esperado"],
                    classe_risco=item["classe_risco"],
                    status=resposta.status_code,
                    obtido=corpo.get("verdict"),
                    score=corpo.get("risk_score"),
                    latencia_ms=parede_ms,
                    modelo=corpo.get("model_version"),
                )
            )
    return casos


def imprimir(relatorio: dict) -> None:
    linha = "=" * 64
    print(f"\n{'ID':<7} | {'Esperado':<14} | {'Obtido':<14} | {'Score':>5} | {'ms':>6}")
    print("-" * 64)
    for c in relatorio["casos"]:
        obtido = c["obtido"] or f"HTTP {c['status']}"
        score = f"{c['score']:.2f}" if c["score"] is not None else "-"
        ms = f"{c['latencia_ms']:.0f}" if c["latencia_ms"] is not None else "-"
        print(f"{c['id']:<7} | {c['esperado']:<14} | {obtido:<14} | {score:>5} | {ms:>6}")

    m = relatorio["matriz_binaria"]
    lat = relatorio["latencia_ms"]
    recusa = relatorio["taxa_recusa_segura"]
    print(f"\n{linha}\nRELATORIO (Docs/Model/01)\n{linha}")
    print(f"Casos: {relatorio['total']} | validos: {relatorio['validos']}")
    print(f"Matriz binaria:  TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}")
    print(f"Recall:          {relatorio['recall']:.4f}  (meta > 0.95)")
    print(f"Precisao:        {relatorio['precisao']:.4f}")
    print(f"F2:              {relatorio['f2']:.4f}  (meta > 0.90)")
    print(f"Acuracia exata:  {relatorio['acuracia_exata']:.4f}")
    if recusa is not None:
        print(f"Recusa segura:   {recusa:.1%}  (meta 100%)")
    print(f"Sem evidencia:   {relatorio['sem_evidencia']}")
    origem = relatorio["origem"]
    print(f"Quem respondeu:  {origem}")
    if origem.get("fallback"):
        print(
            f"ATENCAO: {origem['fallback']} resposta(s) vieram do fallback, nao da LLM. "
            "Numa comparacao de prompts, esses casos nao medem o prompt."
        )
    _imprimir_consistencia(relatorio["casos"])
    if lat["p95"] is not None:
        print(f"Latencia p50/p95: {lat['p50']:.0f} / {lat['p95']:.0f} ms")
    if relatorio["falhas"]:
        print(f"\nFALHAS (fora das metricas): {relatorio['falhas']}")
    print(linha)


def _imprimir_consistencia(casos: list[dict]) -> None:
    """Com repeticoes, mostra os casos em que a LLM mudou de veredito entre rodadas."""
    por_caso: dict[str, list[str]] = {}
    for c in casos:
        if "#" in c["id"]:
            por_caso.setdefault(c["id"].split("#")[0], []).append(c["obtido"] or "falha")
    instaveis = {k: v for k, v in por_caso.items() if len(set(v)) > 1}
    if por_caso:
        print(f"Casos instaveis entre rodadas: {len(instaveis)} de {len(por_caso)}")
        for caso, vereditos in instaveis.items():
            print(f"  {caso}: {', '.join(vereditos)}")


def verificar_metas(relatorio: dict, min_recall, min_f2, min_recusa) -> list[str]:
    reprovadas = []
    if min_recall is not None and relatorio["recall"] < min_recall:
        reprovadas.append(f"recall {relatorio['recall']:.4f} < {min_recall}")
    if min_f2 is not None and relatorio["f2"] < min_f2:
        reprovadas.append(f"F2 {relatorio['f2']:.4f} < {min_f2}")
    recusa = relatorio["taxa_recusa_segura"]
    if min_recusa is not None and recusa is not None and recusa < min_recusa:
        reprovadas.append(f"recusa segura {recusa:.2%} < {min_recusa:.0%}")
    return reprovadas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--url", help="API remota; sem isto, roda em processo")
    parser.add_argument("--token", help="JWT real (modo remoto em producao)")
    parser.add_argument("--intervalo", type=float, help="segundos entre casos")
    parser.add_argument("--saida", type=Path, help="grava o relatorio completo em JSON")
    parser.add_argument("--repeticoes", type=int, default=1, help="roda o dataset N vezes")
    parser.add_argument("--min-recall", type=float)
    parser.add_argument("--min-f2", type=float)
    parser.add_argument("--min-recusa", type=float)
    args = parser.parse_args(argv)

    dataset = carregar_dataset(args.dataset)
    casos = asyncio.run(executar(dataset, args.url, args.token, args.intervalo, args.repeticoes))
    relatorio = calcular(casos)
    imprimir(relatorio)

    if args.saida:
        args.saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), "utf-8")

    if relatorio["falhas"]:
        print("Requisicoes sem resposta: resultado nao confiavel.")
        return 2
    reprovadas = verificar_metas(relatorio, args.min_recall, args.min_f2, args.min_recusa)
    for motivo in reprovadas:
        print(f"META NAO ATINGIDA: {motivo}")
    return 1 if reprovadas else 0


if __name__ == "__main__":
    sys.exit(main())
