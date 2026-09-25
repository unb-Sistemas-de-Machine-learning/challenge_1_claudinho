"""Mede o cold start do Space do Ollama e a cadeia de timeouts de docs/Production/03.

O numero que a doc precisa e medido, nao estimado: quanto tempo o Space leva para
responder a primeira vez depois de dormir, e quanto a cadeia inteira demora quando
nenhum provedor responde e sobra o fallback local.

Tres medicoes, nessa ordem:

1. **frio**: uma geracao com o Space comprovadamente dormindo. E a unica que exige
   preparo manual, porque nao da para forcar o Space a dormir por fora.
2. **cadeia**: o pior caso do pipeline, com a URL do Ollama apontada para um destino
   que nao responde. Mede a soma real dos timeouts ate o fallback local entrar.
3. **quente**: uma segunda geracao logo apos a primeira, como referencia do que o
   cold start custou a mais.

Uso:
    uv run python -m benchmarks.cold_start                  # as tres medicoes
    uv run python -m benchmarks.cold_start --so-frio        # so a 1, com o Space frio
    uv run python -m benchmarks.cold_start --so-cadeia      # so a 2, sem tocar no Space

Para a medicao 1 valer, o Space precisa estar dormindo: o Hugging Face suspende apos
~48 h sem trafego, ou de o sleep manual na aba Settings do Space. Se ele responder em
poucos segundos, estava quente e a medicao nao serve.

ATENCAO: a medicao 2 dispara os timeouts de verdade, entao leva ~160 s para terminar.
"""

import argparse
import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from APP.config import obter_settings
from APP.model.llm import TIMEOUT_EXTERNO_S

TEXTO_PADRAO = "Agua com limao em jejum queima gordura?"


@asynccontextmanager
async def _servidor_mudo():
    """Sobe um servidor que aceita a conexao e nunca responde, e devolve a URL dele.

    Endereco inalcancavel nao serve aqui: a pilha de rede recusa na hora e o timeout
    nunca chega a contar. O que reproduz o Space dormindo e um destino que completa o
    handshake e depois fica calado, estourando o timeout de leitura.
    """
    parar = asyncio.Event()

    async def _atender(_leitor, escritor):
        # Sem o evento de parada, o handler esperaria para sempre e o encerramento do
        # servidor travaria esperando por ele.
        try:
            await parar.wait()
        finally:
            escritor.close()

    servidor = await asyncio.start_server(_atender, "127.0.0.1", 0)
    porta = servidor.sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{porta}/v1"
    finally:
        parar.set()
        servidor.close()
        await servidor.wait_closed()


@dataclass
class Medicao:
    nome: str
    segundos: float
    detalhe: str

    def linha(self) -> str:
        return f"{self.nome:<34} {self.segundos:>7.1f} s   {self.detalhe}"


async def _gerar(base_url: str, modelo: str, api_key: str | None, timeout_s: float) -> str:
    """Uma chamada direta ao provedor, sem o pipeline em volta, para isolar o tempo dele."""
    cabecalhos = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    corpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": TEXTO_PADRAO}],
        "max_tokens": 64,
    }
    async with httpx.AsyncClient(timeout=timeout_s) as cliente:
        resposta = await cliente.post(
            f"{base_url.rstrip('/')}/chat/completions", json=corpo, headers=cabecalhos
        )
        resposta.raise_for_status()
        return resposta.json()["choices"][0]["message"]["content"][:60]


async def _medir_provedor(nome: str, settings) -> Medicao:
    if not settings.llm_base_url:
        return Medicao(nome, 0.0, "LLM_BASE_URL nao configurada — pulada")

    inicio = time.perf_counter()
    try:
        trecho = await _gerar(
            settings.llm_base_url,
            settings.llm_modelo,
            settings.llm_api_key,
            settings.llm_timeout_s,
        )
        detalhe = f'respondeu: "{trecho}..."'
    except httpx.TimeoutException:
        detalhe = f"ESTOUROU o timeout de {settings.llm_timeout_s:.0f} s"
    except httpx.HTTPError as erro:
        detalhe = f"falhou: {type(erro).__name__}"
    return Medicao(nome, time.perf_counter() - inicio, detalhe)


async def _medir_cadeia(settings) -> Medicao:
    """Pior caso: Ollama inalcancavel, reservas tentadas em serie, fallback local no fim."""
    from APP.model.llm import GeracaoIndisponivel, Provedor, gerar_json

    async with _servidor_mudo() as url_muda:
        provedores = [
            Provedor(
                nome="ollama",
                base_url=url_muda,
                modelo=settings.llm_modelo,
                timeout_s=settings.llm_timeout_s,
                aceita_dados_sensiveis=True,
            )
        ]
        # As reservas so entram na cadeia real quando a chave existe; sem ela, a soma
        # medida e menor que a de producao, e o relatorio avisa.
        if settings.gemini_api_key:
            provedores.append(
                Provedor(nome="gemini", base_url=url_muda, modelo=settings.gemini_modelo)
            )
        if settings.openai_api_key:
            provedores.append(
                Provedor(nome="openai", base_url=url_muda, modelo=settings.openai_modelo)
            )

        soma_esperada = sum(p.timeout_s for p in provedores)
        inicio = time.perf_counter()
        try:
            await asyncio.to_thread(
                gerar_json,
                "Responda em JSON.",
                TEXTO_PADRAO,
                provedores,
                dados_sensiveis=False,
            )
            detalhe = "algum provedor respondeu — a medicao nao vale"
        except GeracaoIndisponivel:
            detalhe = f"caiu no fallback local (esperado ~{soma_esperada:.0f} s)"
        decorrido = time.perf_counter() - inicio

    nomes = " -> ".join(p.nome for p in provedores)
    if len(provedores) < 3:
        detalhe += "; reservas sem chave ficaram de fora"
    return Medicao("Cadeia completa ate o fallback", decorrido, f"{nomes}; {detalhe}")


async def principal(args) -> None:
    settings = obter_settings()
    medicoes: list[Medicao] = []

    if not args.so_cadeia:
        print("Medindo a primeira resposta (Space precisa estar frio)...")
        medicoes.append(await _medir_provedor("Ollama, primeira resposta (frio)", settings))

    if not args.so_frio:
        espera_s = settings.llm_timeout_s + 2 * TIMEOUT_EXTERNO_S
        print(f"Medindo a cadeia completa (leva ~{espera_s:.0f} s)...")
        medicoes.append(await _medir_cadeia(settings))

    if not args.so_cadeia and not args.so_frio:
        print("Medindo a resposta ja quente...")
        medicoes.append(await _medir_provedor("Ollama, ja quente (referencia)", settings))

    print("\n--- Resultado ---")
    for medicao in medicoes:
        print(medicao.linha())

    teto_s = 300  # vercel.json, maxDuration. Ver docs/Production/01, secao 3.
    pior = max((m.segundos for m in medicoes), default=0.0)
    print(f"\nTeto da funcao na Vercel: {teto_s} s. Pior caso medido: {pior:.1f} s.")
    print(f"Margem: {teto_s - pior:.1f} s.")
    print("\nRegistre os numeros em docs/Production/03, secao 1.3, com a data de hoje.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--so-frio", action="store_true", help="so a medicao do Space frio")
    parser.add_argument("--so-cadeia", action="store_true", help="so a cadeia de timeouts")
    asyncio.run(principal(parser.parse_args()))
