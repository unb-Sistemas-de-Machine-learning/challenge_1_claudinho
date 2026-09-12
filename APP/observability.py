"""Observabilidade: trace_id, log estruturado e hash de usuario.

Implementa o contrato de log descrito em Docs/Production/02_monitoramento_e_mlops.md,
secao 3. Regras que este modulo existe para garantir:

- UM registro por requisicao, e nao varios eventos parciais. Cada camada enriquece
  o mesmo registro via `registrar_etapa`, e o middleware emite tudo no final.
- NENHUM dado de saude em texto claro. O usuario e identificado por hash e o perfil
  clinico nunca entra no log, so um booleano dizendo se um filtro foi acionado.
- O `trace_id` e o mesmo no log, na resposta da API e no feedback do usuario.
"""

import hashlib
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

_LOGGER_NOME = "claudinho.trace"

# Registro da requisicao em andamento. ContextVar (e nao variavel global) porque o
# FastAPI atende requisicoes concorrentes: cada uma precisa do seu proprio registro.
_registro_atual: ContextVar[dict[str, Any] | None] = ContextVar("registro_atual", default=None)


def configurar_logging() -> None:
    """Manda o log para stdout em linha unica, que e como o provedor coleta."""
    logger = logging.getLogger(_LOGGER_NOME)
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def hash_usuario(token: str) -> str:
    """Identificador estavel do usuario sem expor o token nem o e-mail."""
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()[:16]


def iniciar_registro(endpoint: str, metodo: str) -> dict[str, Any]:
    registro: dict[str, Any] = {
        "trace_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "endpoint": endpoint,
        "method": metodo,
        "user_id_hash": None,
        "status": "success",
        "error": None,
    }
    _registro_atual.set(registro)
    return registro


def obter_trace_id() -> str | None:
    registro = _registro_atual.get()
    return registro["trace_id"] if registro else None


def registrar_etapa(nome: str, dados: dict[str, Any]) -> None:
    """Anexa o resultado de uma etapa do pipeline ao registro da requisicao.

    Chamado por retrieval, generation e guardrails quando esses modulos existirem.
    Fora de uma requisicao (em um script, por exemplo) e um no-op silencioso.
    """
    registro = _registro_atual.get()
    if registro is None:
        return
    registro.setdefault(nome, {}).update(dados)


def registrar_usuario(token: str) -> None:
    registro = _registro_atual.get()
    if registro is not None:
        registro["user_id_hash"] = hash_usuario(token)


def emitir(registro: dict[str, Any]) -> None:
    logging.getLogger(_LOGGER_NOME).info(json.dumps(registro, ensure_ascii=False, default=str))
