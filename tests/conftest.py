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

AUTH = {"Authorization": "Bearer token-de-teste"}


@pytest.fixture
def client():
    return TestClient(app)
