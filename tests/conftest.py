import os

import pytest

# Valores de teste fixados ANTES de importar a aplicacao.
# Usamos atribuicao direta (e nao setdefault) de proposito: o CI define
# SUPABASE_URL/SUPABASE_KEY no ambiente do job, e a suite precisa ser
# hermetica — o mesmo resultado na maquina do dev e no GitHub Actions.
os.environ["SUPABASE_URL"] = "https://teste.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-de-teste"
os.environ["APP_ENV"] = "local"

import json  # noqa: E402
import logging  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from APP.main import app  # noqa: E402
from APP.observabilidade import LOGGER_INFERENCIA  # noqa: E402

AUTH = {"Authorization": "Bearer token-de-teste"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def registros_de_log():
    """Os registros de inferencia emitidos durante o teste, ja decodificados.

    Nao da para usar o caplog do pytest aqui: ele captura pelo logger raiz, e o
    logger de inferencia tem propagate=False de proposito (senao a linha sairia
    duas vezes em producao). Entao ligamos um coletor direto nele.
    """
    coletados: list[dict] = []

    class _Coletor(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            coletados.append(json.loads(record.getMessage()))

    logger = logging.getLogger(LOGGER_INFERENCIA)
    handler = _Coletor()
    logger.addHandler(handler)
    try:
        yield coletados
    finally:
        logger.removeHandler(handler)
