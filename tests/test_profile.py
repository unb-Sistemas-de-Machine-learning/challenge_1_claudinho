"""Testes dos endpoints de perfil.

O modelo de dados espelhado aqui (Docs/Data/01_tipos_e_fontes_de_dados.md) e da
frente de Dados. Quando o schema do Supabase for definido, este arquivo acompanha
`APP/routers/profile.py` e `APP/model/repositorio.py`.
"""

import json

from tests.conftest import AUTH

ROTA = "/api/v1/profile"

PERFIL_COMPLETO = {
    "sex": "F",
    "birth_date": "2003-04-12",
    "height_cm": 165,
    "weight_kg": 60,
    "conditions": ["diabetes_tipo_1"],
    "dietary_restrictions": ["lactose"],
    "routine": "sedentaria",
    "consent_health_data": True,
}


def test_perfil_inexistente_retorna_404(client):
    assert client.get(ROTA, headers=AUTH).status_code == 404


def test_salva_e_recupera_o_perfil(client):
    assert client.put(ROTA, headers=AUTH, json=PERFIL_COMPLETO).status_code == 200

    salvo = client.get(ROTA, headers=AUTH).json()

    assert salvo["conditions"] == ["diabetes_tipo_1"]
    assert salvo["height_cm"] == 165
    assert salvo["routine"] == "sedentaria"


def test_condicoes_de_saude_exigem_consentimento_explicito(client):
    """LGPD Art. 5o, II: condicao clinica e dado pessoal sensivel."""
    resposta = client.put(
        ROTA,
        headers=AUTH,
        json={"conditions": ["gestante"], "consent_health_data": False},
    )

    assert resposta.status_code == 400
    assert "consent_health_data" in resposta.json()["detail"]


def test_perfil_pode_ser_salvo_sem_nenhum_campo(client):
    """O perfil e opcional: o usuario que nao quer informar nada nao pode ser travado."""
    assert client.put(ROTA, headers=AUTH, json={}).status_code == 200


def test_perfil_rejeita_medidas_absurdas(client):
    assert client.put(ROTA, headers=AUTH, json={"height_cm": 400}).status_code == 400
    assert client.put(ROTA, headers=AUTH, json={"weight_kg": 5}).status_code == 400


def test_atualizar_o_perfil_substitui_o_anterior(client):
    client.put(ROTA, headers=AUTH, json=PERFIL_COMPLETO)
    client.put(ROTA, headers=AUTH, json={"sex": "M", "consent_health_data": True})

    salvo = client.get(ROTA, headers=AUTH).json()

    assert salvo["sex"] == "M"
    assert salvo["conditions"] == []


def test_perfil_de_um_usuario_nao_vaza_para_outro(client):
    outro = {"Authorization": "Bearer outro-usuario"}

    client.put(ROTA, headers=AUTH, json=PERFIL_COMPLETO)

    assert client.get(ROTA, headers=outro).status_code == 404


def test_perfil_exige_autenticacao(client):
    assert client.get(ROTA).status_code == 401
    assert client.put(ROTA, json={"sex": "F"}).status_code == 401


def test_log_do_perfil_nao_contem_condicao_clinica(client, logs):
    """Docs/Production/02, secao 3.1: o log guarda so o booleano, nunca a condicao."""
    client.put(ROTA, headers=AUTH, json=PERFIL_COMPLETO)

    assert "diabetes" not in json.dumps(logs[0])
    assert logs[0]["profile"]["has_conditions"] is True
