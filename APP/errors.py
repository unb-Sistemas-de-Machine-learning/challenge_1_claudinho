"""Erros da API no formato do contrato: {"error": "<codigo>", "detail": "..."}."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from APP.observabilidade import adicionar_ao_log


class ApiError(Exception):
    """Erro com codigo do contrato.

    `extras` entra no corpo da resposta e `headers` vai no cabecalho: o 429 do contrato
    devolve `retry_after` no corpo e `Retry-After` no header (Docs/Production/01, secao 2.1).
    """

    def __init__(
        self,
        codigo: str,
        status_code: int,
        detail: str | None = None,
        *,
        extras: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.codigo = codigo
        self.status_code = status_code
        self.detail = detail
        self.extras = extras or {}
        self.headers = headers


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        adicionar_ao_log(status="error", error=exc.codigo)
        corpo: dict[str, object] = {"error": exc.codigo}
        if exc.detail:
            corpo["detail"] = exc.detail
        corpo.update(exc.extras)
        return JSONResponse(status_code=exc.status_code, content=corpo, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError) -> JSONResponse:
        # O contrato define 400/invalid_input, e nao o 422 padrao do FastAPI.
        adicionar_ao_log(status="error", error="invalid_input")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "invalid_input", "detail": _descrever(exc)},
        )


def _descrever(exc: RequestValidationError) -> str:
    """Junta os erros do pydantic em um texto que o app mobile pode exibir.

    O `errors()` cru traz repr de excecao e o dict interno do pydantic — o que
    polui a tela do usuario e expoe detalhe de implementacao.
    """
    mensagens = []
    for erro in exc.errors():
        campo = ".".join(str(parte) for parte in erro["loc"] if parte != "body")
        texto = erro["msg"].removeprefix("Value error, ")
        mensagens.append(f"{campo}: {texto}" if campo else texto)
    return "; ".join(mensagens)
