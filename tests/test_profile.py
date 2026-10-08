"""Perfil de saude (APP/routers/profile.py e APP/repositorios/perfil.py).

O perfil e o que aciona os filtros de grupo de risco do Docs/Ethics/02, e guarda dado
sensivel de saude. Os testes cobrem o contrato da secao 2.3 do Production/01, a regra de
consentimento da LGPD e o que pode (e o que nao pode) sair no log.
"""

from conftest import AUTH

PERFIL_COMPLETO = {
    "sex": "F",
    "birth_date": "1972-04-12",
    "height_cm": 165,
    "weight_kg": 68,
    "conditions": ["diabetes_tipo_2"],
    "dietary_restrictions": ["lactose"],
    "routine": "sedentaria",
    "consent_health_data": True,
}


class TestLeituraEEscrita:
    def test_salva_e_devolve_o_perfil(self, client):
        salvo = client.put("/api/v1/profile", json=PERFIL_COMPLETO, headers=AUTH)
        assert salvo.status_code == 200

        lido = client.get("/api/v1/profile", headers=AUTH)

        assert lido.status_code == 200
        assert lido.json()["conditions"] == ["diabetes_tipo_2"]
        assert lido.json()["routine"] == "sedentaria"

    def test_quem_nunca_preencheu_recebe_404(self, client):
        resposta = client.get("/api/v1/profile", headers=AUTH)

        assert resposta.status_code == 404
        assert resposta.json()["error"] == "profile_not_found"

    def test_put_substitui_o_perfil_inteiro(self, client):
        client.put("/api/v1/profile", json=PERFIL_COMPLETO, headers=AUTH)

        client.put("/api/v1/profile", json={"sex": "F", "routine": "leve"}, headers=AUTH)

        atual = client.get("/api/v1/profile", headers=AUTH).json()
        assert atual["conditions"] == []
        assert atual["routine"] == "leve"

    def test_perfil_vazio_e_valido(self, client):
        """Tudo e opcional: o usuario pode salvar sem informar nada."""
        assert client.put("/api/v1/profile", json={}, headers=AUTH).status_code == 200

    def test_exige_autenticacao(self, client):
        assert client.get("/api/v1/profile").status_code == 401
        assert client.put("/api/v1/profile", json={}).status_code == 401


class TestConsentimentoLGPD:
    def test_condicao_sem_consentimento_e_recusada(self, client):
        corpo = {"conditions": ["diabetes_tipo_2"], "consent_health_data": False}

        resposta = client.put("/api/v1/profile", json=corpo, headers=AUTH)

        assert resposta.status_code == 400
        assert resposta.json()["error"] == "invalid_input"
        assert "consent_health_data" in resposta.json()["detail"]

    def test_restricao_alimentar_nao_exige_consentimento(self, client):
        """Restricao alimentar sozinha nao e dado de saude: vegetariano nao e diagnostico."""
        corpo = {"dietary_restrictions": ["vegetariana"]}

        assert client.put("/api/v1/profile", json=corpo, headers=AUTH).status_code == 200


class TestEntradasAbsurdas:
    def test_condicao_gigante_e_recusada(self, client):
        corpo = {"conditions": ["x" * 5000], "consent_health_data": True}

        assert client.put("/api/v1/profile", json=corpo, headers=AUTH).status_code == 400

    def test_lista_de_condicoes_sem_fim_e_recusada(self, client):
        corpo = {"conditions": ["diabetes_tipo_2"] * 50, "consent_health_data": True}

        assert client.put("/api/v1/profile", json=corpo, headers=AUTH).status_code == 400

    def test_data_de_nascimento_no_futuro_e_recusada(self, client):
        """O campo alimenta filtro por idade: data no futuro viraria idade negativa."""
        resposta = client.put("/api/v1/profile", json={"birth_date": "2090-01-01"}, headers=AUTH)

        assert resposta.status_code == 400
        assert "birth_date" in resposta.json()["detail"]

    def test_medidas_impossiveis_sao_recusadas(self, client):
        alta = client.put("/api/v1/profile", json={"height_cm": 400}, headers=AUTH)
        leve = client.put("/api/v1/profile", json={"weight_kg": 5}, headers=AUTH)

        assert alta.status_code == 400
        assert leve.status_code == 400


class TestLog:
    def test_o_log_nao_carrega_a_condicao_clinica(self, client, registros_de_log):
        client.put("/api/v1/profile", json=PERFIL_COMPLETO, headers=AUTH)

        registro = registros_de_log[0]
        texto_do_registro = str(registro)

        assert "diabetes_tipo_2" not in texto_do_registro
        assert registro["profile"] == {
            "has_conditions": True,
            "has_restrictions": True,
            "consent_health_data": True,
        }

    def test_o_log_identifica_o_usuario_por_hash(self, client, registros_de_log):
        """Sem isso nao da para fazer a triagem por usuario do Docs/Production/02."""
        client.put("/api/v1/profile", json={}, headers=AUTH)

        assert registros_de_log[0]["user_id_hash"].startswith("sha256:")
