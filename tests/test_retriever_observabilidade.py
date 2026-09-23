"""O retriever precisa deixar rastro no log, no sucesso e na falha.

Docs/Production/02, secao 2.1: a deteccao de drift depende de `similarity_max` e
`low_coverage` por consulta. E uma falha do Supabase nao pode se passar, no
monitoramento, por "a base nao tem estudos sobre esse tema".
"""

from APP.model import retriever
from tests.conftest import AUTH

ROTA = "/api/v1/check-claim"
CORPO = {"text": "gengibre acelera o metabolismo?"}


class _Resultado:
    def __init__(self, data):
        self.data = data


class _SupabaseFalso:
    def __init__(self, chunks=None, artigos=None, falhar_rpc=False, falhar_tabela=False):
        self._chunks = chunks or []
        self._artigos = artigos or []
        self._falhar_rpc = falhar_rpc
        self._falhar_tabela = falhar_tabela
        self.consultas_a_tabela = 0

    def rpc(self, _nome, _parametros):
        if self._falhar_rpc:
            raise ConnectionError("supabase fora do ar")
        return self

    def table(self, _nome):
        return self

    def select(self, _colunas):
        self.consultas_a_tabela += 1
        if self._falhar_tabela:
            raise ConnectionError("supabase fora do ar")
        return _Execucao(self._artigos)

    def execute(self):
        return _Resultado(self._chunks)


class _Execucao:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return _Resultado(self._data)


def _usar(monkeypatch, supabase):
    monkeypatch.setattr(retriever, "obter_supabase", lambda: supabase)


def test_falha_do_supabase_fica_registrada_no_log(client, monkeypatch, registros_de_log):
    _usar(monkeypatch, _SupabaseFalso(falhar_rpc=True))

    resposta = client.post(ROTA, headers=AUTH, json=CORPO)

    # Falha de infraestrutura vira 503, e nao "sem evidencia", que seria uma resposta falsa.
    assert resposta.status_code == 503
    assert resposta.json()["error"] == "upstream_unavailable"
    assert registros_de_log[-1]["retrieval"]["erro"] == "ConnectionError"


def test_recuperacao_registra_cobertura_para_drift(client, monkeypatch, registros_de_log):
    chunks = [
        {"chunk_id": "c1", "article_id": "a1", "similaridade": 0.81, "conteudo": "x"},
        {"chunk_id": "c2", "article_id": "a1", "similaridade": 0.72, "conteudo": "y"},
    ]
    _usar(monkeypatch, _SupabaseFalso(chunks=chunks))

    client.post(ROTA, headers=AUTH, json=CORPO)

    recuperacao = registros_de_log[-1]["retrieval"]
    assert recuperacao["chunks"] == 2
    assert recuperacao["chunk_ids"] == ["c1", "c2"]
    assert recuperacao["similarity_max"] == 0.81
    assert recuperacao["low_coverage"] is False


def test_similaridade_baixa_conta_como_sem_cobertura(client, monkeypatch, registros_de_log):
    chunks = [{"chunk_id": "c1", "article_id": "a1", "similaridade": 0.71, "conteudo": "x"}]
    _usar(monkeypatch, _SupabaseFalso(chunks=chunks))

    client.post(ROTA, headers=AUTH, json=CORPO)

    assert registros_de_log[-1]["retrieval"]["low_coverage"] is True


def test_log_de_recuperacao_nao_contem_o_texto_do_usuario(client, monkeypatch, registros_de_log):
    chunks = [{"chunk_id": "c1", "article_id": "a1", "similaridade": 0.9, "conteudo": "x"}]
    _usar(monkeypatch, _SupabaseFalso(chunks=chunks))

    client.post(ROTA, headers=AUTH, json={"text": "tenho diabetes, gengibre ajuda?"})

    assert "diabetes" not in str(registros_de_log[-1])


def test_falha_ao_carregar_o_catalogo_nao_fica_em_cache(monkeypatch):
    fora_do_ar = _SupabaseFalso(falhar_tabela=True)
    _usar(monkeypatch, fora_do_ar)
    assert retriever.obter_metadados_artigos() == {}

    de_volta = _SupabaseFalso(artigos=[{"id": "a1", "title": "Estudo"}])
    _usar(monkeypatch, de_volta)

    assert retriever.obter_metadados_artigos() == {"a1": {"id": "a1", "title": "Estudo"}}


def test_catalogo_carregado_com_sucesso_e_reaproveitado(monkeypatch):
    supabase = _SupabaseFalso(artigos=[{"id": "a1", "title": "Estudo"}])
    _usar(monkeypatch, supabase)

    retriever.obter_metadados_artigos()
    retriever.obter_metadados_artigos()

    assert supabase.consultas_a_tabela == 1


def test_guardrail_acionado_fica_registrado(client, registros_de_log):
    client.post(
        ROTA, headers=AUTH, json={"text": "Como vomitar depois de comer para nao engordar?"}
    )

    assert registros_de_log[-1]["guardrails"]["safe_refusal"] is True
