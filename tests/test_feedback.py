"""POST /feedback — contrato em Docs/Production/01, secao 2.2."""

import json
import uuid

import pytest

from tests.conftest import AUTH

ROTA = "/api/v1/feedback"
TRACE_ID = "7c1f2a90-3e4b-4d21-9f10-0b2a5c8e4d33"


@pytest.fixture
def repositorio():
    """Repositorio limpo por teste, injetado no lugar do global."""
    from APP.main import app
    from APP.repositorios.feedback import RepositorioEmMemoria, obter_repositorio_de_feedback

    repo = RepositorioEmMemoria()
    app.dependency_overrides[obter_repositorio_de_feedback] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


def test_registra_o_feedback_e_devolve_201(client, repositorio):
    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={
            "trace_id": TRACE_ID,
            "rating": "down",
            "reason": "fonte_irrelevante",
            "comment": "a resposta nao falou sobre gastrite",
        },
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "registered"
    uuid.UUID(corpo["feedback_id"])


def test_o_feedback_chega_ao_repositorio(client, repositorio):
    client.post(ROTA, headers=AUTH, json={"trace_id": TRACE_ID, "rating": "up"})

    assert len(repositorio.registrados) == 1
    guardado = repositorio.registrados[0]
    assert guardado.trace_id == TRACE_ID
    assert guardado.rating == "up"


def test_exige_autenticacao(client, repositorio):
    resposta = client.post(ROTA, json={"trace_id": TRACE_ID, "rating": "up"})

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "unauthorized"
    assert repositorio.registrados == []


@pytest.mark.parametrize(
    "corpo",
    [
        {"trace_id": "nao-e-uuid", "rating": "down"},
        {"trace_id": TRACE_ID, "rating": "talvez"},
        {"trace_id": TRACE_ID, "rating": "down", "reason": "motivo_inventado"},
        {"rating": "down"},
    ],
    ids=["trace_id invalido", "rating invalido", "reason fora da lista", "sem trace_id"],
)
def test_recusa_payload_invalido(client, repositorio, corpo):
    resposta = client.post(ROTA, headers=AUTH, json=corpo)

    assert resposta.status_code == 400
    assert resposta.json()["error"] == "invalid_input"
    assert repositorio.registrados == []


def test_aceita_os_seis_motivos_do_contrato(client, repositorio):
    motivos = [
        "fonte_irrelevante",
        "resposta_confusa",
        "parece_errado",
        "tom_julgador",
        "nao_respondeu",
        "outro",
    ]

    for motivo in motivos:
        resposta = client.post(
            ROTA, headers=AUTH, json={"trace_id": TRACE_ID, "rating": "down", "reason": motivo}
        )
        assert resposta.status_code == 201, motivo

    assert len(repositorio.registrados) == len(motivos)


def test_o_comentario_do_usuario_nunca_vai_para_o_log(client, repositorio, registros_de_log):
    """O comentario e texto livre e pode conter dado de saude
    ("tenho diabetes e..."). Docs/Production/02, secao 3.1: isso nao entra no log."""
    comentario = "tenho diabetes tipo 1 e a resposta nao considerou isso"

    client.post(
        ROTA,
        headers=AUTH,
        json={"trace_id": TRACE_ID, "rating": "down", "reason": "outro", "comment": comentario},
    )

    assert comentario not in json.dumps(registros_de_log[0], ensure_ascii=False)


def test_o_log_amarra_o_feedback_a_execucao_avaliada(client, repositorio, registros_de_log):
    client.post(
        ROTA, headers=AUTH, json={"trace_id": TRACE_ID, "rating": "down", "reason": "parece_errado"}
    )

    registro = registros_de_log[0]
    assert registro["endpoint"] == ROTA
    assert registro["feedback"]["trace_id_avaliado"] == TRACE_ID
    assert registro["feedback"]["rating"] == "down"
    assert registro["feedback"]["reason"] == "parece_errado"
