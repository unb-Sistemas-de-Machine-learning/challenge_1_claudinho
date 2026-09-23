"""Teste de estresse do /check-claim contra os SLAs de Docs/Production/03.

Dispara checagens concorrentes e, ao mesmo tempo, sonda o /health. A sonda e o que
revela um event loop travado: se o pipeline bloquear o servidor, o /health demora
tanto quanto a LLM, mesmo que as checagens em si terminem.

Uso:
    uv run python -m benchmarks.estresse
    uv run python -m benchmarks.estresse --usuarios 30 --requisicoes 90
    uv run python -m benchmarks.estresse --url http://127.0.0.1:8000

Cada usuario virtual tem identidade propria, entao o servidor alvo precisa estar em
APP_ENV=local (que aceita qualquer token). Contra producao, com JWT real, o rate limit
de 10/min por usuario barraria a carga, o que por si so ja e um resultado valido.

ATENCAO: com GEMINI_API_KEY configurada, cada requisicao chama a LLM de verdade e
consome cota. Comece com poucos usuarios.
"""

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

from benchmarks._cliente import cabecalho, criar_cliente
from benchmarks.metricas import percentil

ROTA = "/api/v1/check-claim"
TEXTO_PADRAO = "Agua com limao em jejum queima gordura?"

# Docs/Production/03, secao 1.
SLA_P95_MS = 5000
SLA_HEALTH_MS = 1000
INTERVALO_SONDA_S = 0.2


async def _usuario(cliente, identidade, quantidade, texto, latencias, status):
    for _ in range(quantidade):
        inicio = time.perf_counter()
        try:
            resposta = await cliente.post(ROTA, headers=cabecalho(identidade), json={"text": texto})
            status[resposta.status_code] += 1
            if resposta.status_code == 200:
                latencias.append((time.perf_counter() - inicio) * 1000)
        except Exception as erro:
            status[type(erro).__name__] += 1


async def _sonda_de_saude(cliente, parar: asyncio.Event, latencias):
    while not parar.is_set():
        inicio = time.perf_counter()
        try:
            await cliente.get("/health")
            latencias.append((time.perf_counter() - inicio) * 1000)
        except Exception:
            latencias.append(float("inf"))
        await asyncio.sleep(INTERVALO_SONDA_S)


async def executar(
    usuarios: int, requisicoes: int, url: str | None = None, texto: str = TEXTO_PADRAO
) -> dict:
    por_usuario, sobra = divmod(requisicoes, usuarios)
    latencias: list[float] = []
    latencias_health: list[float] = []
    status: Counter = Counter()

    async with criar_cliente(url) as cliente:
        parar = asyncio.Event()
        sonda = asyncio.create_task(_sonda_de_saude(cliente, parar, latencias_health))

        inicio = time.perf_counter()
        await asyncio.gather(
            *(
                _usuario(
                    cliente,
                    f"estresse-{i}",
                    por_usuario + (1 if i < sobra else 0),
                    texto,
                    latencias,
                    status,
                )
                for i in range(usuarios)
            )
        )
        duracao_s = time.perf_counter() - inicio

        parar.set()
        await sonda

    return {
        "usuarios": usuarios,
        "requisicoes": requisicoes,
        "duracao_s": round(duracao_s, 2),
        "vazao_rps": round(requisicoes / duracao_s, 2) if duracao_s else None,
        "status": {str(k): v for k, v in status.items()},
        "sucesso": status.get(200, 0),
        "latencia_ms": {
            "p50": percentil(latencias, 50),
            "p95": percentil(latencias, 95),
            "p99": percentil(latencias, 99),
            "max": max(latencias) if latencias else None,
        },
        "health_ms": {
            "amostras": len(latencias_health),
            "p95": percentil(latencias_health, 95),
            "max": max(latencias_health) if latencias_health else None,
        },
    }


def avaliar_sla(relatorio: dict, sla_p95_ms: float, sla_health_ms: float) -> list[str]:
    violacoes = []
    if relatorio["sucesso"] < relatorio["requisicoes"]:
        violacoes.append(f"{relatorio['requisicoes'] - relatorio['sucesso']} requisicoes falharam")
    p95 = relatorio["latencia_ms"]["p95"]
    if p95 is not None and p95 > sla_p95_ms:
        violacoes.append(f"p95 {p95:.0f} ms > {sla_p95_ms:.0f} ms")
    saude = relatorio["health_ms"]["max"]
    if saude is not None and saude > sla_health_ms:
        violacoes.append(f"/health chegou a {saude:.0f} ms: event loop travado?")
    return violacoes


def imprimir(relatorio: dict) -> None:
    lat, saude = relatorio["latencia_ms"], relatorio["health_ms"]

    def ms(v):
        return "-" if v is None else f"{v:.0f}"

    print("=" * 60)
    print(f"ESTRESSE: {relatorio['usuarios']} usuarios, {relatorio['requisicoes']} requisicoes")
    print("=" * 60)
    print(f"Duracao:          {relatorio['duracao_s']} s  ({relatorio['vazao_rps']} req/s)")
    print(f"Status:           {relatorio['status']}")
    percentis = " / ".join(ms(lat[k]) for k in ("p50", "p95", "p99", "max"))
    print(f"Latencia p50/p95/p99/max: {percentis} ms")
    print(f"/health p95/max:  {ms(saude['p95'])} / {ms(saude['max'])} ms", end="")
    print(f"  ({saude['amostras']} sondas)")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", help="API remota; sem isto, roda em processo")
    parser.add_argument("--usuarios", type=int, default=10)
    parser.add_argument("--requisicoes", type=int, default=30)
    parser.add_argument("--texto", default=TEXTO_PADRAO)
    parser.add_argument("--sla-p95-ms", type=float, default=SLA_P95_MS)
    parser.add_argument("--sla-health-ms", type=float, default=SLA_HEALTH_MS)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args(argv)

    if args.requisicoes > args.usuarios * 10:
        print("Aviso: mais de 10 requisicoes por usuario estouram o rate limit (10/min).")

    relatorio = asyncio.run(executar(args.usuarios, args.requisicoes, args.url, args.texto))
    imprimir(relatorio)
    if args.saida:
        args.saida.write_text(json.dumps(relatorio, indent=2), "utf-8")

    violacoes = avaliar_sla(relatorio, args.sla_p95_ms, args.sla_health_ms)
    for v in violacoes:
        print(f"SLA VIOLADO: {v}")
    return 1 if violacoes else 0


if __name__ == "__main__":
    sys.exit(main())
