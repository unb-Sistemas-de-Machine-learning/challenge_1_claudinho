import json
import logging
import os

import pytest

# Valores de teste fixados ANTES de importar a aplicacao.
# Usamos atribuicao direta (e nao setdefault) de proposito: o CI define
# SUPABASE_URL/SUPABASE_KEY no ambiente do job, e a suite precisa ser
# hermetica — o mesmo resultado na maquina do dev e no GitHub Actions.
os.environ["SUPABASE_URL"] = "https://teste.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-de-teste"
os.environ["APP_ENV"] = "local"

from fastapi.testclient import TestClient  # noqa: E402

from APP.main import app  # noqa: E402
from APP.model import repositorio_feedback, repositorio_perfil  # noqa: E402
from APP.ratelimit import limiter  # noqa: E402

AUTH = {"Authorization": "Bearer token-de-teste"}


@pytest.fixture
def client():
    # O repositorio e em memoria e o contador de rate limit e global:
    # sem reset, um teste enxerga o estado deixado pelo anterior.
    repositorio_feedback.limpar()
    repositorio_perfil.limpar()
    limiter.reset()
    return TestClient(app)


class _ColetorDeLogs(logging.Handler):
    """Coleta os registros estruturados emitidos durante um teste.

    Necessario porque o logger de trace usa `propagate=False` e escreve direto em
    stdout — o caplog do pytest, que se prende ao logger raiz, nao enxergaria nada.
    """

    def __init__(self):
        super().__init__()
        self.registros: list[dict] = []

    def emit(self, record):
        self.registros.append(json.loads(record.getMessage()))


@pytest.fixture
def logs():
    handler = _ColetorDeLogs()
    logger = logging.getLogger("claudinho.trace")
    logger.addHandler(handler)
    yield handler.registros
    logger.removeHandler(handler)
