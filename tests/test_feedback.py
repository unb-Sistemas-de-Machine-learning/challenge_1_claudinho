import uuid

from tests.conftest import AUTH

ROTA = "/api/v1/feedback"


def test_registra_feedback_positivo(client):
    resposta = client.post(ROTA, headers=AUTH, json={"trace_id": str(uuid.uuid4()), "rating": "up"})

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "registered"
    uuid.UUID(resposta.json()["feedback_id"])


def test_feedback_negativo_exige_motivo(client):
    """Sem motivo o feedback nao e triavel: nao da para saber se o problema foi
    recuperacao, geracao ou tom (Docs/Production/02, secao 4)."""
    resposta = client.post(
        ROTA, headers=AUTH, json={"trace_id": str(uuid.uuid4()), "rating": "down"}
    )

    assert resposta.status_code == 400
    assert "reason" in resposta.json()["detail"]


def test_feedback_negativo_com_motivo_valido(client):
    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={
            "trace_id": str(uuid.uuid4()),
            "rating": "down",
            "reason": "fonte_irrelevante",
            "comment": "nao respondeu sobre gastrite",
        },
    )

    assert resposta.status_code == 201


def test_feedback_rejeita_motivo_fora_da_lista(client):
    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={"trace_id": str(uuid.uuid4()), "rating": "down", "reason": "sei_la"},
    )

    assert resposta.status_code == 400


def test_feedback_rejeita_trace_id_que_nao_e_uuid(client):
    resposta = client.post(ROTA, headers=AUTH, json={"trace_id": "abc", "rating": "up"})

    assert resposta.status_code == 400


def test_feedback_exige_autenticacao(client):
    resposta = client.post(ROTA, json={"trace_id": str(uuid.uuid4()), "rating": "up"})

    assert resposta.status_code == 401
