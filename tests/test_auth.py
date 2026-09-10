"""Testes da validacao de JWT.

Os demais arquivos da suite rodam no modo local (sem segredo configurado). Aqui o
segredo e injetado por override de dependencia para exercitar o caminho de producao.
"""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from APP.auth import verificar_configuracao
from APP.config import Settings, obter_settings
from APP.main import app

# Comprimento >= 32 bytes: HS256 emite aviso abaixo disso (RFC 7518, secao 3.2).
SEGREDO = "segredo-de-teste-com-32-bytes-ok!"
ROTA = "/api/v1/profile"


def _settings_com_jwt() -> Settings:
    return Settings(
        supabase_url="https://teste.supabase.co",
        supabase_key="chave-de-teste",
        app_env="local",
        supabase_jwt_secret=SEGREDO,
    )


def _token(sub="usuario-123", segredo=SEGREDO, expira_em=3600, audiencia="authenticated"):
    return jwt.encode(
        {"sub": sub, "aud": audiencia, "exp": int(time.time()) + expira_em},
        segredo,
        algorithm="HS256",
    )


@pytest.fixture
def client_com_jwt():
    app.dependency_overrides[obter_settings] = _settings_com_jwt
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_aceita_token_valido(client_com_jwt):
    resposta = client_com_jwt.put(
        ROTA, headers={"Authorization": f"Bearer {_token()}"}, json={"sex": "F"}
    )

    assert resposta.status_code == 200


def test_rejeita_token_assinado_com_outro_segredo(client_com_jwt):
    forjado = _token(segredo="outro-segredo-igualmente-longo-32b")

    resposta = client_com_jwt.get(ROTA, headers={"Authorization": f"Bearer {forjado}"})

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token invalido"


def test_rejeita_token_expirado(client_com_jwt):
    resposta = client_com_jwt.get(
        ROTA, headers={"Authorization": f"Bearer {_token(expira_em=-10)}"}
    )

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token expirado"


def test_rejeita_token_de_outra_audiencia(client_com_jwt):
    """Um token de service_role nao pode passar como token de usuario logado."""
    resposta = client_com_jwt.get(
        ROTA, headers={"Authorization": f"Bearer {_token(audiencia='service_role')}"}
    )

    assert resposta.status_code == 401


def test_rejeita_string_que_nao_e_jwt(client_com_jwt):
    resposta = client_com_jwt.get(ROTA, headers={"Authorization": "Bearer banana"})

    assert resposta.status_code == 401


def test_identidade_e_estavel_entre_tokens_diferentes_do_mesmo_usuario(client_com_jwt):
    """O perfil e indexado pelo `sub`, nao pelo token: sair e entrar de novo gera um
    token novo, e o perfil precisa continuar la."""
    primeiro = {"Authorization": f"Bearer {_token(expira_em=3600)}"}
    client_com_jwt.put(ROTA, headers=primeiro, json={"sex": "F", "height_cm": 165})

    segundo = {"Authorization": f"Bearer {_token(expira_em=7200)}"}
    assert primeiro != segundo

    salvo = client_com_jwt.get(ROTA, headers=segundo)

    assert salvo.status_code == 200
    assert salvo.json()["height_cm"] == 165


def test_configuracao_recusa_subir_sem_segredo_fora_do_local():
    settings = Settings(
        supabase_url="https://teste.supabase.co",
        supabase_key="chave",
        app_env="production",
        supabase_jwt_secret=None,
    )

    with pytest.raises(RuntimeError, match="SUPABASE_JWT_SECRET"):
        verificar_configuracao(settings)


def test_configuracao_aceita_local_sem_segredo():
    settings = Settings(
        supabase_url="https://teste.supabase.co", supabase_key="chave", app_env="local"
    )

    verificar_configuracao(settings)
