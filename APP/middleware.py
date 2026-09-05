"""Middleware que emite um registro de log por requisicao.

Docs/Production/02, secao 3.1: "Um registro por requisicao, nao varios" —
evita ter que fazer join entre eventos parciais na hora de analisar.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from APP.observabilidade import (
    definir_contexto,
    emitir,
    hash_de_usuario,
    limpar_contexto,
    novo_registro,
)

# O provedor de hospedagem bate no /health a cada 30 segundos e o Swagger e
# estatico: logar isso afogaria os registros de inferencia de verdade.
ROTAS_SEM_LOG = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"})


class LoggingDeInferencia(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ROTAS_SEM_LOG:
            return await call_next(request)

        registro = novo_registro(
            trace_id=str(uuid.uuid4()),
            endpoint=request.url.path,
            user_id_hash=hash_de_usuario(request.headers.get("authorization")),
        )
        token_do_contexto = definir_contexto(registro)
        inicio = time.perf_counter()

        try:
            resposta = await call_next(request)
        except Exception as erro:
            # Registra e deixa subir: o middleware observa, nao engole falha.
            registro["status"] = "error"
            registro["error"] = type(erro).__name__
            raise
        else:
            # Os handlers de APP/errors.py ja gravam status/error quando o erro
            # tem um codigo do contrato. Aqui so preenchemos o que sobrou.
            registro.setdefault("status", "success" if resposta.status_code < 400 else "error")
            registro.setdefault("error", None)
            return resposta
        finally:
            registro["performance"]["total_latency_ms"] = int((time.perf_counter() - inicio) * 1000)
            emitir(registro)
            limpar_contexto(token_do_contexto)
