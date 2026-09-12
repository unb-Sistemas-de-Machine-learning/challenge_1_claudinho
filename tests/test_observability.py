import json

from tests.conftest import AUTH

ROTA = "/api/v1/check-claim"


def test_cada_requisicao_emite_um_unico_registro(client, logs):
    client.post(ROTA, headers=AUTH, json={"text": "ovo faz mal?"})

    assert len(logs) == 1
    assert logs[0]["endpoint"] == ROTA
    assert logs[0]["status"] == "success"
    assert logs[0]["performance"]["total_latency_ms"] >= 0


def test_trace_id_e_o_mesmo_no_log_no_header_e_no_corpo(client, logs):
    resposta = client.post(ROTA, headers=AUTH, json={"text": "detox funciona?"})

    assert logs[0]["trace_id"] == resposta.json()["trace_id"] == resposta.headers["X-Trace-Id"]


def test_log_nao_contem_o_texto_da_duvida_nem_o_token(client, logs):
    duvida = "tenho diabetes tipo 1, posso fazer jejum de 24h?"

    client.post(ROTA, headers=AUTH, json={"text": duvida})

    bruto = json.dumps(logs[0])
    # A duvida pode conter dado de saude: so o comprimento vai para o log.
    assert "diabetes" not in bruto
    assert "token-de-teste" not in bruto
    assert logs[0]["input"]["raw_length"] == len(duvida)


def test_usuario_aparece_apenas_como_hash(client, logs):
    client.post(ROTA, headers=AUTH, json={"text": "gluten faz mal?"})

    assert logs[0]["user_id_hash"].startswith("sha256:")


def test_requisicao_sem_token_e_registrada_como_erro(client, logs):
    client.post(ROTA, json={"text": "ovo?"})

    assert logs[0]["status"] == "error"
    assert logs[0]["http_status"] == 401
    assert logs[0]["user_id_hash"] is None
