"""Exclusao do perfil de saude (docs/Ethics/02, secao 4).

A politica de expurgo homologada pela frente de Etica exige duas coisas: exclusao
imediata a pedido da pessoa (este endpoint) e expurgo automatico apos 6 meses de
inatividade (funcao agendada em deploy/sql/001_profiles_e_feedback.sql).
"""

from conftest import AUTH

from APP.repositorios.perfil import obter_repositorio_de_perfil
from APP.schemas import Profile

ROTA = "/api/v1/profile"
IDENTIDADE = AUTH["Authorization"].removeprefix("Bearer ")
PERFIL = Profile(conditions=["diabetes_tipo_2"], consent_health_data=True)


def test_apaga_o_perfil_e_o_get_volta_a_404(client):
    obter_repositorio_de_perfil().salvar(IDENTIDADE, PERFIL)

    resposta = client.delete(ROTA, headers=AUTH)

    assert resposta.status_code == 204
    assert client.get(ROTA, headers=AUTH).status_code == 404


def test_apagar_sem_perfil_tambem_responde_204(client):
    """Distinguir "nao existia" de "foi apagado" contaria a quem tem o token se havia
    dado de saude guardado."""
    assert client.delete(ROTA, headers=AUTH).status_code == 204


def test_nao_apaga_o_perfil_de_outra_pessoa(client):
    obter_repositorio_de_perfil().salvar("outra-pessoa", PERFIL)

    client.delete(ROTA, headers=AUTH)

    assert obter_repositorio_de_perfil().buscar("outra-pessoa") is not None


def test_exige_autenticacao(client):
    assert client.delete(ROTA).status_code == 401


def test_o_log_diz_que_apagou_sem_dizer_o_que_havia(client, registros_de_log):
    obter_repositorio_de_perfil().salvar(IDENTIDADE, PERFIL)

    client.delete(ROTA, headers=AUTH)

    registro = registros_de_log[-1]
    assert registro["profile"] == {"apagado": True}
    assert "diabetes" not in str(registro)
