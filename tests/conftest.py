import os

import pytest

# Valores de teste fixados ANTES de importar a aplicacao.
# Usamos atribuicao direta (e nao setdefault) de proposito: o CI define
# SUPABASE_URL/SUPABASE_KEY no ambiente do job, e a suite precisa ser
# hermetica — o mesmo resultado na maquina do dev e no GitHub Actions.
os.environ["SUPABASE_URL"] = "https://teste.supabase.co"
os.environ["SUPABASE_KEY"] = "chave-de-teste"
os.environ["APP_ENV"] = "local"
# Provedores de LLM desligados, mesmo que o .env do dev tenha chaves: variavel de
# ambiente vence o .env. Sem isto, a suite chamaria o Gemini de verdade na maquina de
# quem tem a chave configurada, gastando cota e ficando diferente do CI.
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_API_KEY"] = ""
# Mesma logica para autenticacao e embeddings: com o SUPABASE_JWT_SECRET de verdade no .env,
# o modo local (que aceita o token de teste) desligaria e toda a suite viraria 401; com a
# EMBEDDINGS_URL, a suite chamaria o Hugging Face e gastaria a cota gratuita.
os.environ["SUPABASE_JWT_SECRET"] = ""
os.environ["EMBEDDINGS_URL"] = ""
os.environ["EMBEDDINGS_TOKEN"] = ""
os.environ["ORIGENS_PERMITIDAS"] = "[]"

import json  # noqa: E402
import logging  # noqa: E402
import uuid  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from APP.auth import ALGORITMO, AUDIENCIA  # noqa: E402
from APP.config import obter_settings  # noqa: E402
from APP.main import app  # noqa: E402
from APP.model import retriever  # noqa: E402
from APP.model.database import obter_supabase  # noqa: E402
from APP.observabilidade import LOGGER_INFERENCIA  # noqa: E402
from APP.ratelimit import limpar as limpar_limites  # noqa: E402
from APP.repositorios.feedback import obter_repositorio_de_feedback  # noqa: E402
from APP.repositorios.perfil import obter_repositorio_de_perfil  # noqa: E402
from tests._dubles import SupabaseFalso  # noqa: E402

AUTH = {"Authorization": "Bearer token-de-teste"}

SEGREDO_DE_TESTE = "segredo-de-teste-nao-usar-em-producao"


@pytest.fixture(autouse=True)
def estado_do_processo():
    """Zera o que vive no processo entre um teste e outro.

    Repositorios em memoria e contador de rate limit sao globais de modulo. Sem esta
    limpeza, um teste enxerga o perfil gravado por outro e a ordem dos arquivos passa a
    mudar o resultado da suite. E autouse de proposito: quem esquecer de pedir a fixture
    nao fica com um teste que passa por engano.
    """
    limpar_estado()
    yield
    limpar_estado()


@pytest.fixture(autouse=True)
def base_de_teste(monkeypatch):
    """Banco e modelo de embeddings falsos para TODA a suite.

    - Nao baixa o modelo real (mais de 1 GB, a cada execucao do CI).
    - Nao tenta conectar no Supabase: sem rede, o resultado nao depende de DNS.
    - Por padrao a busca devolve um trecho; o teste pode trocar pedindo a fixture:
      `base_de_teste.chunks = []` simula uma base sem estudos sobre o tema.
    """
    base = SupabaseFalso()
    monkeypatch.setattr(retriever, "gerar_embedding_consulta", lambda _texto: [0.0] * 768)
    monkeypatch.setattr(retriever, "obter_supabase", lambda: base)
    retriever.limpar_cache_de_artigos()
    yield base
    retriever.limpar_cache_de_artigos()


def limpar_estado() -> None:
    limpar_limites()
    obter_repositorio_de_feedback().limpar()
    obter_repositorio_de_perfil().limpar()
    # O pipeline cria o client do Supabase ao buscar evidencias; sem limpar, o teste que
    # confere que o import nao cria client passa a depender da ordem da suite.
    obter_supabase.cache_clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def client_com_jwt(monkeypatch):
    """TestClient com a validacao de JWT ligada, como em staging e producao.

    A configuracao e lida por `obter_settings`, que tem cache. Mexer na variavel de
    ambiente e limpar o cache deixa o modo valendo para TODO mundo na requisicao
    (rota, middleware de log e rate limit), o que um `dependency_overrides` nao faria:
    middleware e rate limit chamam `obter_settings()` direto, fora do FastAPI.
    """
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SEGREDO_DE_TESTE)
    obter_settings.cache_clear()
    try:
        yield TestClient(app)
    finally:
        obter_settings.cache_clear()


def token_de(sub: str = "usuario-123", **alteracoes) -> str:
    """Monta um JWT igual ao que o Supabase Auth emite.

    O `jti` aleatorio existe para que duas chamadas seguidas gerem tokens DIFERENTES do
    mesmo usuario, como acontece a cada renovacao de sessao. Sem ele, os dois tokens
    sairiam byte a byte iguais no mesmo segundo e o teste de renovacao passaria a toa.
    """
    payload = {
        "sub": sub,
        "aud": AUDIENCIA,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "jti": uuid.uuid4().hex,
    }
    payload.update(alteracoes.pop("payload", {}))
    segredo = alteracoes.pop("segredo", SEGREDO_DE_TESTE)
    return jwt.encode(payload, segredo, algorithm=ALGORITMO)


def auth_de(sub: str = "usuario-123", **alteracoes) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_de(sub, **alteracoes)}"}


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
