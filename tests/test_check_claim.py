import base64
import uuid

from tests.conftest import AUTH

ROTA = "/api/v1/check-claim"


def test_devolve_o_contrato_completo_para_uma_duvida_em_texto(client):
    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={
            "input_type": "text",
            "text": "vi no insta que agua com limao em jejum queima gordura, e verdade?",
            "use_profile": True,
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()

    # Campos obrigatorios do contrato (Docs/Production/01 secao 2.1)
    esperados = {
        "trace_id",
        "canonical_claim",
        "verdict",
        "risk_score",
        "risk_level",
        "answer",
        "sources",
        "disclaimer",
        "cached",
        "latency_ms",
        "model_version",
        "prompt_version",
    }
    assert esperados.issubset(corpo.keys())

    uuid.UUID(corpo["trace_id"])  # levanta ValueError se nao for um UUID valido
    assert corpo["verdict"] in {
        "seguro",
        "cautela",
        "desinformacao",
        "sem_evidencia",
        "recusa_segura",
    }
    assert 0.0 <= corpo["risk_score"] <= 1.0
    assert corpo["cached"] is False
    assert len(corpo["sources"]) >= 1
    assert corpo["sources"][0]["doi"]


def test_cada_requisicao_recebe_um_trace_id_diferente(client):
    corpo = {"input_type": "text", "text": "ovo aumenta colesterol?"}

    primeira = client.post(ROTA, headers=AUTH, json=corpo).json()
    segunda = client.post(ROTA, headers=AUTH, json=corpo).json()

    assert primeira["trace_id"] != segunda["trace_id"]


def test_recusa_requisicao_sem_nenhum_campo_de_entrada(client):
    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={"input_type": "text", "text": None, "url": None, "image_base64": None},
    )

    assert resposta.status_code == 400
    assert resposta.json()["error"] == "invalid_input"


def test_recusa_requisicao_sem_token(client):
    resposta = client.post(ROTA, json={"input_type": "text", "text": "ovo faz mal?"})

    assert resposta.status_code == 401
    assert resposta.json()["error"] == "unauthorized"


def test_recusa_imagem_acima_de_5_mb(client):
    imagem_gigante = base64.b64encode(b"x" * (5 * 1024 * 1024 + 1)).decode()

    resposta = client.post(
        ROTA,
        headers=AUTH,
        json={"input_type": "image", "image_base64": imagem_gigante},
    )

    assert resposta.status_code == 413
    assert resposta.json()["error"] == "payload_too_large"


def test_detalhe_do_erro_e_legivel_e_nao_vaza_interno_do_python(client):
    resposta = client.post(ROTA, headers=AUTH, json={"input_type": "text"})

    detalhe = resposta.json()["detail"]
    assert "preencha ao menos um entre text, url e image_base64" in detalhe
    # O app mobile mostra esse texto: nao pode conter repr de excecao nem dict do pydantic.
    assert "ValueError" not in detalhe
    assert "'ctx'" not in detalhe
