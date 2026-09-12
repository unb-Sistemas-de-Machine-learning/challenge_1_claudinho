"""Middleware que abre, cronometra e fecha o registro de cada requisicao."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from APP.observability import emitir, iniciar_registro, obter_trace_id


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        registro = iniciar_registro(request.url.path, request.method)
        inicio = time.perf_counter()

        try:
            resposta = await call_next(request)
        except Exception as erro:
            # Excecao nao tratada: registra e deixa subir para o handler do FastAPI,
            # senao o erro sumiria do log justamente no caso que mais importa.
            registro["status"] = "error"
            registro["error"] = type(erro).__name__
            registro.setdefault("performance", {})["total_latency_ms"] = _decorrido(inicio)
            emitir(registro)
            raise

        registro["http_status"] = resposta.status_code
        if resposta.status_code >= 400:
            registro["status"] = "error"
        registro.setdefault("performance", {})["total_latency_ms"] = _decorrido(inicio)
        emitir(registro)

        # Devolve o trace_id ao cliente: e o que o app manda de volta em /feedback e
        # o que o usuario informa quando reporta uma resposta errada.
        trace_id = obter_trace_id()
        if trace_id:
            resposta.headers["X-Trace-Id"] = trace_id
        return resposta


def _decorrido(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)
