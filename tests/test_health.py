def test_health_responde_ok_sem_autenticacao(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
