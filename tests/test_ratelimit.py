from tests.conftest import AUTH

ROTA = "/api/v1/check-claim"


def test_bloqueia_apos_o_limite_por_minuto(client):
    corpo = {"text": "agua com limao emagrece?"}

    for _ in range(10):
        assert client.post(ROTA, headers=AUTH, json=corpo).status_code == 200

    excedida = client.post(ROTA, headers=AUTH, json=corpo)

    assert excedida.status_code == 429
    assert excedida.json()["error"] == "rate_limited"
    assert excedida.json()["retry_after"] > 0
    assert excedida.headers["Retry-After"]


def test_usuarios_diferentes_tem_cotas_independentes(client):
    corpo = {"text": "ovo aumenta colesterol?"}
    outro = {"Authorization": "Bearer outro-usuario"}

    for _ in range(10):
        client.post(ROTA, headers=AUTH, json=corpo)

    # O primeiro usuario estourou a cota; o segundo nao pode ser penalizado por isso.
    assert client.post(ROTA, headers=AUTH, json=corpo).status_code == 429
    assert client.post(ROTA, headers=outro, json=corpo).status_code == 200
