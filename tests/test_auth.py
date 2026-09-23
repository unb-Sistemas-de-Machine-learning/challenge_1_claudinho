"""Validacao do JWT do Supabase Auth (APP/auth.py).

O que importa aqui e a identidade ser ESTAVEL e o modo de producao recusar tudo que
nao veio do Supabase. Um token aceito por engano da acesso ao perfil de saude de
outra pessoa.
"""

import pytest
from conftest import auth_de, token_de

from APP.auth import verificar_configuracao
from APP.config import Settings

PERFIL = {"sex": "F", "routine": "leve"}


def _settings(**valores) -> Settings:
    base = {
        "supabase_url": "https://teste.supabase.co",
        "supabase_key": "chave",
        "app_env": "production",
        "supabase_jwt_secret": "segredo",
        "origens_permitidas": ["https://claudinho.app"],
    }
    base.update(valores)
    return Settings(**base)


class TestTokensRecusados:
    def test_sem_header_devolve_401(self, client_com_jwt):
        resposta = client_com_jwt.get("/api/v1/profile")
        assert resposta.status_code == 401
        assert resposta.json()["error"] == "unauthorized"

    def test_token_expirado_devolve_401(self, client_com_jwt):
        from datetime import UTC, datetime, timedelta

        vencido = auth_de(payload={"exp": datetime.now(UTC) - timedelta(minutes=1)})
        resposta = client_com_jwt.get("/api/v1/profile", headers=vencido)
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "token expirado"

    def test_assinatura_de_outro_segredo_devolve_401(self, client_com_jwt):
        forjado = auth_de(segredo="segredo-do-atacante-com-tamanho-suficiente")
        resposta = client_com_jwt.get("/api/v1/profile", headers=forjado)
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "token invalido"

    def test_audiencia_errada_devolve_401(self, client_com_jwt):
        # O Supabase emite `aud: authenticated` para usuario logado. Outro valor pode ser
        # um token de servico, que nao representa pessoa nenhuma.
        outro_publico = auth_de(payload={"aud": "service_role"})
        resposta = client_com_jwt.get("/api/v1/profile", headers=outro_publico)
        assert resposta.status_code == 401

    def test_token_sem_sub_devolve_401(self, client_com_jwt):
        sem_identidade = {"Authorization": f"Bearer {token_de(payload={'sub': ''})}"}
        resposta = client_com_jwt.get("/api/v1/profile", headers=sem_identidade)
        assert resposta.status_code == 401
        assert resposta.json()["detail"] == "token sem identificacao de usuario"


class TestIdentidade:
    def test_token_valido_passa(self, client_com_jwt):
        resposta = client_com_jwt.put("/api/v1/profile", json=PERFIL, headers=auth_de())
        assert resposta.status_code == 200

    def test_a_identidade_sobrevive_a_renovacao_do_token(self, client_com_jwt):
        """Dois tokens diferentes do mesmo usuario tem que achar o mesmo perfil.

        O Supabase rotaciona o access token de hora em hora. Se a identidade fosse o
        token, o perfil de saude sumiria a cada renovacao.
        """
        client_com_jwt.put("/api/v1/profile", json=PERFIL, headers=auth_de("lucas"))

        outro_token = auth_de("lucas")
        resposta = client_com_jwt.get("/api/v1/profile", headers=outro_token)

        assert resposta.status_code == 200
        assert resposta.json()["routine"] == "leve"

    def test_um_usuario_nao_enxerga_o_perfil_do_outro(self, client_com_jwt):
        client_com_jwt.put("/api/v1/profile", json=PERFIL, headers=auth_de("lucas"))

        resposta = client_com_jwt.get("/api/v1/profile", headers=auth_de("renata"))

        assert resposta.status_code == 404


class TestModoLocal:
    def test_aceita_qualquer_token_nao_vazio(self, client):
        resposta = client.put(
            "/api/v1/profile", json=PERFIL, headers={"Authorization": "Bearer qualquer-coisa"}
        )
        assert resposta.status_code == 200

    def test_header_sem_token_continua_recusado(self, client):
        resposta = client.get("/api/v1/profile", headers={"Authorization": "Bearer "})
        assert resposta.status_code == 401


class TestTravaDeConfiguracao:
    """A trava roda na subida da aplicacao (APP/main.py).

    As duas variaveis quebram em silencio quando faltam: sem o segredo a API aceita
    qualquer token, sem as origens o navegador bloqueia o app inteiro. Melhor nao subir.
    """

    def test_local_nao_exige_nada(self):
        verificar_configuracao(_settings(app_env="local", supabase_jwt_secret=None))

    def test_producao_sem_segredo_do_jwt_sobe(self):
        """Projetos atuais do Supabase validam pelas chaves publicas, sem segredo.
        A garantia de que ninguem entra sem token valido fora do local esta em
        tests/test_auth_jwks.py::test_fora_do_local_token_qualquer_e_recusado."""
        verificar_configuracao(_settings(supabase_jwt_secret=None))

    def test_producao_sem_origens_nao_sobe(self):
        with pytest.raises(RuntimeError, match="ORIGENS_PERMITIDAS"):
            verificar_configuracao(_settings(origens_permitidas=[]))

    def test_producao_configurada_sobe(self):
        verificar_configuracao(_settings())
