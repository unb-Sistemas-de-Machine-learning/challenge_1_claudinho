"""Rate limiting (APP/ratelimit.py).

Tres coisas precisam valer, e as tres ja falharam em alguma versao:
1. a cota segue a identidade, nao o token, senao renovar o token zera o limite;
2. requisicao sem token e com corpo invalido tambem conta, senao da para martelar a
   verificacao de JWT a vontade;
3. o `retry_after` diz o tempo real ate liberar, e nao um numero fixo.
"""

import asyncio
from types import SimpleNamespace

import pytest
from conftest import AUTH, auth_de
from limits import parse

from APP.errors import ApiError
from APP.ratelimit import LIMITE_CHECK_CLAIM, limitar

CHECAGEM = {"input_type": "text", "text": "agua com limao queima gordura?"}
# Lido da constante para o teste acompanhar uma mudanca de limite em vez de quebrar.
LIMITE = LIMITE_CHECK_CLAIM.amount


def _checar(client, headers=AUTH, corpo=CHECAGEM):
    return client.post("/api/v1/check-claim", json=corpo, headers=headers)


class TestLimitePorUsuario:
    def test_libera_ate_o_limite_e_barra_a_proxima(self, client):
        for tentativa in range(LIMITE):
            assert _checar(client).status_code == 200, f"tentativa {tentativa + 1}"

        resposta = _checar(client)

        assert resposta.status_code == 429
        assert resposta.json()["error"] == "rate_limited"

    def test_usuarios_diferentes_tem_cotas_separadas(self, client_com_jwt):
        for _ in range(LIMITE):
            _checar(client_com_jwt, auth_de("lucas"))

        assert _checar(client_com_jwt, auth_de("lucas")).status_code == 429
        assert _checar(client_com_jwt, auth_de("renata")).status_code == 200

    def test_renovar_o_token_nao_zera_a_cota(self, client_com_jwt):
        """Regressao: a chave e a identidade, nao o token.

        O Supabase rotaciona o access token de hora em hora e o refresh e disparado pelo
        cliente. Com o token como chave, bastaria renovar para ter limite infinito.
        """
        for _ in range(LIMITE):
            _checar(client_com_jwt, auth_de("lucas"))

        token_novo = auth_de("lucas")  # mesmo `sub`, token diferente

        assert _checar(client_com_jwt, token_novo).status_code == 429


class TestTrafegoQueNaoChegaNaRota:
    def test_requisicao_sem_token_tambem_conta(self, client):
        """Regressao: o limite roda antes da autenticacao.

        Enquanto o limite era um decorador da funcao do endpoint, o FastAPI barrava a
        requisicao no 401 antes de contar, e a verificacao de JWT ficava sem protecao.
        """
        respostas = [_checar(client, headers={}) for _ in range(LIMITE + 1)]

        assert respostas[0].status_code == 401
        assert respostas[-1].status_code == 429

    def test_corpo_invalido_tambem_conta(self, client):
        respostas = [_checar(client, corpo={}) for _ in range(LIMITE + 1)]

        assert respostas[0].status_code == 400
        assert respostas[-1].status_code == 429


class TestRespostaDo429:
    def test_diz_quanto_esperar_no_corpo_e_no_header(self, client):
        for _ in range(LIMITE):
            _checar(client)

        resposta = _checar(client)
        retry_after = resposta.json()["retry_after"]

        # A janela e de um minuto e as chamadas acima foram agora: o tempo restante tem
        # que ser proximo de 60, nunca zero e nunca um valor fixo maior que a janela.
        assert 0 < retry_after <= 60
        assert resposta.headers["Retry-After"] == str(retry_after)

    def test_retry_after_acompanha_a_janela(self):
        """Regressao: o valor era fixo em 60, qualquer que fosse a janela.

        Com um limite por hora, mandar o cliente tentar de novo em 60 segundos o joga
        num laco de 429 pelos 59 minutos seguintes. O teste chama a dependencia direto
        porque nenhuma rota usa janela de hora hoje.
        """
        checar = limitar(parse("1/hour"))
        # `state` existe porque a identidade e resolvida uma vez por requisicao e
        # guardada ali (APP/auth.py:resolver_identidade).
        pedido = SimpleNamespace(
            headers={}, client=SimpleNamespace(host="203.0.113.7"), state=SimpleNamespace()
        )

        asyncio.run(checar(pedido))
        with pytest.raises(ApiError) as excecao:
            asyncio.run(checar(pedido))

        assert excecao.value.extras["retry_after"] > 60

    def test_escrita_nao_usa_a_cota_do_check_claim(self, client):
        """O /feedback tem limite proprio (LIMITE_ESCRITA), maior que o da checagem."""
        corpo = {"trace_id": "7c1f2a90-3e4b-4d21-9f10-0b2a5c8e4d33", "rating": "up"}

        respostas = [
            client.post("/api/v1/feedback", json=corpo, headers=AUTH) for _ in range(LIMITE + 1)
        ]

        assert all(resposta.status_code == 201 for resposta in respostas)
