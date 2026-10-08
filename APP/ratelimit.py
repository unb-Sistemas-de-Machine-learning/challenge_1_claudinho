"""Rate limiting por identidade (Docs/Production/03, secao 2.2).

Contador em memoria: suficiente para uma instancia unica, que e o cenario do MVP.
Ao escalar para mais de uma instancia, troque `MemoryStorage` pelo storage do Redis
(Upstash) sem mudar o resto do arquivo.

Duas decisoes que nao sao obvias
--------------------------------

**A checagem e uma dependencia de rota, nao um decorador na funcao.** O FastAPI so
chama a funcao do endpoint depois de resolver as dependencias e validar o corpo. Um
limite aplicado ali nunca conta requisicao sem token nem com corpo invalido, que e
justo o trafego que a gente quer conter: sem o limite antes da autenticacao, da para
martelar a verificacao de JWT a vontade. Dependencia declarada na rota roda antes.

**A chave e a identidade, nao o token.** O Supabase rotaciona o access token de hora
em hora e o refresh e disparado pelo cliente. Com o token como chave, bastaria renovar
para zerar a cota. Usamos o mesmo hash que vai para o log (`hash_de_usuario`), entao da
para cruzar o balde do limite com o `user_id_hash` do registro de inferencia.
"""

import math
import time

from fastapi import Request
from limits import RateLimitItem, parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from APP.auth import resolver_identidade
from APP.errors import ApiError
from APP.observabilidade import hash_de_usuario

# Limites do MVP. O /check-claim e caro (LLM + busca vetorial), escrita e barata.
LIMITE_CHECK_CLAIM = parse("10/minute")
LIMITE_ESCRITA = parse("30/minute")

# Janela deslizante e nao janela fixa: com janela fixa da para fazer o dobro do limite
# na virada (tudo no fim de uma janela, tudo no inicio da seguinte).
_armazenamento = MemoryStorage()
_limitador = MovingWindowRateLimiter(_armazenamento)


async def _chave(request: Request) -> str:
    """Identidade do usuario quando o token vale, IP quando nao vale.

    O IP e so a rede de seguranca para quem ainda nao autenticou. Note que todo mundo
    atras do mesmo NAT (o wi-fi da faculdade) divide esse balde, entao ele e proposital
    e deliberadamente mais generoso de usar apenas onde nao ha identidade.
    """
    identidade = await resolver_identidade(request)
    if identidade:
        return f"usuario:{hash_de_usuario(identidade)}"
    cliente = request.client.host if request.client else "desconhecido"
    return f"ip:{cliente}"


def limitar(limite: RateLimitItem):
    """Devolve a dependencia que aplica `limite` na rota.

    Use em `dependencies=[Depends(limitar(LIMITE_X))]`, nunca como decorador da funcao.
    """

    async def checar_limite(request: Request) -> None:
        chave = await _chave(request)
        if _limitador.hit(limite, chave):
            return

        # O tempo real ate liberar, e nao um numero fixo: se o limite virar algo por hora,
        # um "tente em 60s" chuta o cliente para um laco de 429 pelo resto da janela.
        estatisticas = _limitador.get_window_stats(limite, chave)
        segundos = max(1, math.ceil(estatisticas.reset_time - time.time()))
        raise ApiError(
            "rate_limited",
            429,
            extras={"retry_after": segundos},
            headers={"Retry-After": str(segundos)},
        )

    return checar_limite


def limpar() -> None:
    """Zera os contadores. Usado pelos testes para isolar um caso do outro."""
    _armazenamento.reset()
