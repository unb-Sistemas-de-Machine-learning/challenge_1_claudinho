"""Log estruturado de inferencia — Docs/Production/02, secao 3.

Cada requisicao gera UM registro JSON em stdout, costurado pelo `trace_id`.
E esse mesmo trace_id que aparece na resposta da API e no /feedback: e a chave
que liga "o usuario reclamou" a "esta execucao exata, com estes chunks e esta
versao de prompt".

Como o contexto funciona
------------------------
O middleware cria um dicionario por requisicao e o guarda em um ContextVar
ANTES de chamar a rota. A rota enriquece esse mesmo dicionario chamando
`adicionar_ao_log(...)`.

Detalhe que nao e obvio: o BaseHTTPMiddleware do Starlette roda a aplicacao em
uma task separada, entao um `ContextVar.set()` feito DENTRO da rota nao volta
para o middleware. Guardar um dicionario mutavel e defini-lo antes da chamada
contorna isso — as duas tasks enxergam o mesmo objeto, e as alteracoes de uma
aparecem na outra.
"""

import hashlib
import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

LOGGER_INFERENCIA = "claudinho.inferencia"

_logger = logging.getLogger(LOGGER_INFERENCIA)
_contexto: ContextVar[dict[str, Any] | None] = ContextVar("contexto_de_log", default=None)

# Blocos do pipeline de RAG. Ficam no formato desde ja, com None, para que o
# consumidor do log (Langfuse, Grafana) veja sempre o mesmo schema. Passam a
# ser preenchidos quando cada etapa do pipeline existir.
BLOCOS_DO_PIPELINE = ("nlp", "retrieval", "generation", "guardrails")


def novo_registro(trace_id: str, endpoint: str, user_id_hash: str | None) -> dict[str, Any]:
    registro: dict[str, Any] = {
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "user_id_hash": user_id_hash,
        "endpoint": endpoint,
        "input": None,
        "output": None,
        "performance": {},
    }
    for bloco in BLOCOS_DO_PIPELINE:
        registro[bloco] = None
    return registro


def definir_contexto(registro: dict[str, Any]):
    return _contexto.set(registro)


def limpar_contexto(token) -> None:
    _contexto.reset(token)


def contexto_atual() -> dict[str, Any] | None:
    return _contexto.get()


def trace_id_atual() -> str | None:
    contexto = _contexto.get()
    return contexto["trace_id"] if contexto else None


def adicionar_ao_log(**blocos: Any) -> None:
    """Enriquece o registro da requisicao atual.

    Dicionarios sao mesclados no que ja existe (para o middleware poder gravar
    a latencia sem apagar o que a rota escreveu em `performance`); os demais
    valores sobrescrevem. Fora de uma requisicao, nao faz nada.
    """
    registro = _contexto.get()
    if registro is None:
        return

    for chave, valor in blocos.items():
        if isinstance(valor, dict) and isinstance(registro.get(chave), dict):
            registro[chave].update(valor)
        else:
            registro[chave] = valor


def hash_de_usuario(authorization: str | None) -> str | None:
    """Identificador estavel do usuario, nunca o valor em claro.

    Docs/Production/02, secao 3.1: dado de saude e identidade nao entram no log.
    Hoje a identidade disponivel e o token do header; quando o APP/auth.py passar
    a validar o JWT de verdade, troque a entrada pela claim `sub` do token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


def emitir(registro: dict[str, Any]) -> None:
    _logger.info(json.dumps(registro, ensure_ascii=False, default=str))


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Liga o logger de inferencia ao stdout.

    Sem isso a aplicacao roda, os testes passam (o pytest captura o log pelo
    proprio framework) e nada aparece no console do servidor. O provedor de
    hospedagem coleta o stdout do processo, entao e ali que o registro precisa
    sair — em linha unica e JSON puro, sem prefixo de nivel ou timestamp do
    logging, para quem consome conseguir parsear.

    Idempotente: chamar duas vezes nao duplica o handler (e a linha do log).
    """
    logger = logging.getLogger(LOGGER_INFERENCIA)
    logger.setLevel(nivel)
    # Nao propaga: se o root tiver handler, a linha sairia duas vezes.
    logger.propagate = False

    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
