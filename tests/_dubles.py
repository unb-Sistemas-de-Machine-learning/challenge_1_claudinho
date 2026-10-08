"""Dubles de teste compartilhados: banco (Supabase) e provedor de LLM falsos.

Substituem os ganchos que existiam dentro do codigo de producao (os
`if "teste.supabase.co" in settings.supabase_url`). O codigo de producao nao sabe mais
que esta sendo testado; quem decide o que o banco e a LLM devolvem e o teste.
"""

from APP.model.llm import Provedor

CHUNK_PADRAO = {
    "chunk_id": "chunk_teste_01",
    "article_id": "artigo_teste_01",
    "titulo": "Efeitos metabolicos de compostos citricos: revisao sistematica",
    "conteudo": (
        "Nao foram observadas diferencas significativas no gasto energetico entre os "
        "grupos que consumiram suco de limao e o grupo controle."
    ),
    "similaridade": 0.86,
}

ARTIGO_PADRAO = {
    "id": "artigo_teste_01",
    "title": "Efeitos metabolicos de compostos citricos: revisao sistematica",
    "author": "Silva, R.; Almeida, C.",
    "published_at": "2021-06-01",
    "metadata": {"doi": "10.1590/teste", "revista": "Revista de Nutricao"},
}

PROVEDOR_FALSO = Provedor(nome="falso", base_url="http://llm.falso/v1", modelo="modelo-teste")


class SupabaseFalso:
    """Imita o client do Supabase o suficiente para o retriever.

    Aceita qualquer encadeamento (`table().select().ilike().execute()`, `rpc().execute()`)
    e devolve o conteudo configurado para a tabela ou funcao chamada. Tabelas sem conteudo
    configurado (a TBCA, por exemplo) voltam vazias.
    """

    def __init__(self, chunks=None, artigos=None):
        self.chunks = [dict(CHUNK_PADRAO)] if chunks is None else chunks
        self.artigos = [dict(ARTIGO_PADRAO)] if artigos is None else artigos
        self.chamadas_rpc = 0
        self._alvo = None

    def rpc(self, _nome, _parametros):
        self.chamadas_rpc += 1
        self._alvo = "rpc"
        return self

    def table(self, nome):
        self._alvo = nome
        return self

    def __getattr__(self, _nome):
        # select, ilike, eq, limit...: qualquer filtro so devolve o proprio objeto.
        return lambda *args, **kwargs: self

    def execute(self):
        dados = {"rpc": self.chunks, "articles": self.artigos}.get(self._alvo, [])
        return _Resultado(dados)


class _Resultado:
    def __init__(self, data):
        self.data = data
