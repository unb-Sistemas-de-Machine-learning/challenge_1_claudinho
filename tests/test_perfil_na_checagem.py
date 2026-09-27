"""O perfil de saude entra na checagem (issue #25 do front).

Tres efeitos: os avisos de Etica passam a valer pelo perfil, e nao so pelo texto da
pergunta; o dado de saude nao pode ir para provedor externo; e o perfil e opcional,
entao falha ao busca-lo nao pode derrubar a checagem.
"""

import pytest
from conftest import AUTH

from APP.main import app
from APP.model import disclaimers
from APP.repositorios.perfil import obter_repositorio_de_perfil
from APP.schemas import Profile

ROTA = "/api/v1/check-claim"
PERGUNTA = {"text": "posso comer manga todo dia?"}


IDENTIDADE = AUTH["Authorization"].removeprefix("Bearer ")


def _guardar(perfil: Profile, usuario: str = IDENTIDADE) -> None:
    # No modo local a identidade e o proprio token (APP/auth.py), entao e ela que indexa
    # o perfil.
    obter_repositorio_de_perfil().salvar(usuario, perfil)


@pytest.fixture
def geracao_espiada(monkeypatch):
    """Captura os argumentos da geracao, para ver o que foi marcado como sensivel."""
    from APP.model import generator

    chamadas = []
    original = generator.gerar_resposta_grounded

    def espiao(*args, **kwargs):
        chamadas.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr("APP.model.pipeline.gerar_resposta_grounded", espiao)
    return chamadas


def test_condicao_do_perfil_gera_o_aviso_mesmo_sem_a_pessoa_escrever(client):
    _guardar(Profile(conditions=["diabetes_tipo_2"], consent_health_data=True))

    resposta = client.post(ROTA, headers=AUTH, json=PERGUNTA)

    assert disclaimers.CONDICOES_CLINICAS in resposta.json()["disclaimer"]


def test_gestacao_no_perfil_gera_o_aviso_de_pre_natal(client):
    _guardar(Profile(conditions=["gestante"], consent_health_data=True))

    resposta = client.post(ROTA, headers=AUTH, json=PERGUNTA)

    assert disclaimers.GESTANTES_E_LACTANTES in resposta.json()["disclaimer"]


def test_perfil_so_entra_quando_o_app_pede(client):
    _guardar(Profile(conditions=["diabetes_tipo_2"], consent_health_data=True))

    resposta = client.post(ROTA, headers=AUTH, json={**PERGUNTA, "use_profile": False})

    assert disclaimers.CONDICOES_CLINICAS not in resposta.json()["disclaimer"]


def test_perfil_com_condicao_marca_a_geracao_como_sensivel(client, geracao_espiada):
    """Docs/Ethics/02: dado de saude nao vai para provedor externo."""
    _guardar(Profile(conditions=["diabetes_tipo_2"], consent_health_data=True))

    client.post(ROTA, headers=AUTH, json=PERGUNTA)

    assert geracao_espiada[-1]["dados_sensiveis"] is True


def test_sem_perfil_a_geracao_nao_e_sensivel(client, geracao_espiada):
    client.post(ROTA, headers=AUTH, json=PERGUNTA)

    assert geracao_espiada[-1]["dados_sensiveis"] is False


def test_falha_ao_buscar_o_perfil_nao_derruba_a_checagem(client, registros_de_log):
    class _RepositorioQuebrado:
        def buscar(self, _usuario):
            raise ConnectionError("supabase fora do ar")

    # dependency_overrides, e nao monkeypatch no modulo: o FastAPI guarda a funcao da
    # dependencia no import da rota, entao trocar o nome depois nao teria efeito.
    app.dependency_overrides[obter_repositorio_de_perfil] = lambda: _RepositorioQuebrado()

    resposta = client.post(ROTA, headers=AUTH, json=PERGUNTA)

    app.dependency_overrides.clear()
    assert resposta.status_code == 200
    assert registros_de_log[-1]["profile"]["erro"] == "ConnectionError"


def test_o_log_diz_que_usou_o_perfil_sem_dizer_o_que_tem_nele(client, registros_de_log):
    _guardar(Profile(conditions=["diabetes_tipo_2"], consent_health_data=True))

    client.post(ROTA, headers=AUTH, json=PERGUNTA)

    registro = registros_de_log[-1]
    assert registro["profile"] == {"usado": True, "has_conditions": True}
    assert "diabetes" not in str(registro)
