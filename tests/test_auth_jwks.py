"""Tokens assinados com chave assimetrica, o padrao do Supabase desde outubro de 2025.

A API valida com a chave PUBLICA do projeto. Os testes geram um par de chaves de verdade e
substituem so a busca das chaves publicas (que, em producao, vem do SUPABASE_URL).
"""

import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from APP import auth
from APP.config import obter_settings
from APP.main import app

ROTA = "/api/v1/profile"


class _Chave:
    def __init__(self, chave):
        self.key = chave


class _ChavesPublicasFalsas:
    """Imita o PyJWKClient: devolve a chave publica do projeto, ou falha como ele falharia."""

    def __init__(self, chave_publica, falha=None):
        self.chave_publica = chave_publica
        self.falha = falha

    def get_signing_key_from_jwt(self, _token):
        if self.falha:
            raise self.falha
        return _Chave(self.chave_publica)


@pytest.fixture
def par_de_chaves():
    privada = ec.generate_private_key(ec.SECP256R1())
    return privada, privada.public_key()


@pytest.fixture
def producao(monkeypatch, par_de_chaves):
    """API como em producao: APP_ENV=production e SEM segredo do JWT."""
    _, publica = par_de_chaves
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ORIGENS_PERMITIDAS", '["https://app.exemplo"]')
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    obter_settings.cache_clear()
    chaves = _ChavesPublicasFalsas(publica)
    monkeypatch.setattr(auth, "_chaves_publicas", lambda _url: chaves)
    try:
        yield TestClient(app), chaves
    finally:
        obter_settings.cache_clear()


def _token(chave_privada, algoritmo="ES256", **payload_extra):
    payload = {
        "sub": "usuario-es256",
        "aud": auth.AUDIENCIA,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "jti": uuid.uuid4().hex,
        **payload_extra,
    }
    return jwt.encode(payload, chave_privada, algorithm=algoritmo, headers={"kid": "chave-1"})


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_token_es256_valido_passa(producao, par_de_chaves):
    cliente, _ = producao
    privada, _ = par_de_chaves

    resposta = cliente.put(ROTA, headers=_headers(_token(privada)), json={"sex": "F"})

    assert resposta.status_code == 200


def test_token_assinado_por_outra_chave_e_recusado(producao):
    cliente, _ = producao
    intrusa = ec.generate_private_key(ec.SECP256R1())

    resposta = cliente.get(ROTA, headers=_headers(_token(intrusa)))

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "token invalido"


def test_token_es256_expirado(producao, par_de_chaves):
    cliente, _ = producao
    privada, _ = par_de_chaves
    vencido = _token(privada, exp=int(time.time()) - 10)

    resposta = cliente.get(ROTA, headers=_headers(vencido))

    assert resposta.json()["detail"] == "token expirado"


def test_fora_do_local_token_qualquer_e_recusado(producao):
    """A garantia central: sem APP_ENV=local, nao existe modo que aceite qualquer token."""
    cliente, _ = producao

    assert cliente.get(ROTA, headers=_headers("banana")).status_code == 401


def test_token_hs256_sem_segredo_configurado_e_recusado(producao):
    cliente, _ = producao
    hs256 = jwt.encode({"sub": "x", "aud": auth.AUDIENCIA}, "chute-de-segredo", algorithm="HS256")

    assert cliente.get(ROTA, headers=_headers(hs256)).status_code == 401


def test_confusao_de_algoritmo_e_recusada(producao, par_de_chaves):
    """Ataque classico: assinar um HS256 usando a chave PUBLICA (que e publica!) como segredo."""
    cliente, _ = producao
    _, publica = par_de_chaves
    pem = publica.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    forjado = _hs256_com_chave_publica(pem)

    assert cliente.get(ROTA, headers=_headers(forjado)).status_code == 401


def _hs256_com_chave_publica(pem: bytes) -> str:
    # O PyJWT se recusa a assinar HS256 com uma chave PEM, justamente para evitar este
    # ataque; o token forjado e montado a mao, como um atacante faria.
    import base64
    import hashlib
    import hmac
    import json

    def b64(dados: bytes) -> str:
        return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()

    cabecalho = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    corpo = b64(json.dumps({"sub": "atacante", "aud": "authenticated"}).encode())
    assinatura = hmac.new(pem, f"{cabecalho}.{corpo}".encode(), hashlib.sha256).digest()
    return f"{cabecalho}.{corpo}.{b64(assinatura)}"


def test_algoritmo_none_e_recusado(producao):
    cliente, _ = producao
    sem_assinatura = jwt.encode({"sub": "x", "aud": auth.AUDIENCIA}, None, algorithm="none")

    assert cliente.get(ROTA, headers=_headers(sem_assinatura)).status_code == 401


def test_chave_desconhecida_e_recusada(producao, par_de_chaves):
    cliente, chaves = producao
    privada, _ = par_de_chaves
    chaves.falha = jwt.PyJWKClientError("kid nao encontrado")

    assert cliente.get(ROTA, headers=_headers(_token(privada))).status_code == 401


def test_falha_ao_buscar_as_chaves_responde_503(producao, par_de_chaves):
    """Supabase fora do ar e infraestrutura, nao token invalido."""
    cliente, chaves = producao
    privada, _ = par_de_chaves
    chaves.falha = jwt.PyJWKClientConnectionError("sem rede")

    resposta = cliente.get(ROTA, headers=_headers(_token(privada)))

    assert resposta.status_code == 503
    assert resposta.json()["error"] == "upstream_unavailable"


def test_url_das_chaves_publicas_e_a_do_projeto():
    auth._chaves_publicas.cache_clear()
    cliente = auth._chaves_publicas("https://projeto.supabase.co/")

    assert cliente.uri == "https://projeto.supabase.co/auth/v1/.well-known/jwks.json"
