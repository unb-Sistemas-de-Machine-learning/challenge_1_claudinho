"""Rate limiting conforme Docs/Production/03_escalabilidade_e_desempenho.md, secao 2.2.

Contador em memoria: suficiente para uma instancia unica, que e o cenario do MVP.
Ao escalar para mais de uma instancia o `storage_uri` passa a apontar para o Redis
do Upstash, sem mudanca no resto do codigo.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from APP.observability import hash_usuario

LIMITE_CHECK_CLAIM = "10/minute"
LIMITE_ESCRITA = "30/minute"


def _chave(request: Request) -> str:
    """Limita por usuario quando ha token, e por IP quando nao ha.

    Sem isso, todo mundo atras do mesmo NAT (o wi-fi da faculdade, por exemplo)
    dividiria a mesma cota e um usuario derrubaria os outros.
    """
    autorizacao = request.headers.get("authorization", "")
    if autorizacao.startswith("Bearer "):
        token = autorizacao.removeprefix("Bearer ").strip()
        if token:
            return hash_usuario(token)
    return get_remote_address(request)


# headers_enabled fica desligado de proposito: com ele o slowapi exige um parametro
# `response: Response` em toda rota limitada, o que polui as assinaturas. O
# Retry-After que o app precisa e devolvido pelo handler abaixo.
limiter = Limiter(key_func=_chave, headers_enabled=False)


def registrar_rate_limit(app: FastAPI) -> None:
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _excedido(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        # O contrato define {"error": "rate_limited", "retry_after": N},
        # e nao o corpo padrao do slowapi.
        retry_after = int(getattr(exc, "retry_after", 60) or 60)
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limited", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )
