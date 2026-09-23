from datetime import date
from unittest.mock import MagicMock, patch

from APP.model.retriever import (
    _extrair_data_publicacao,
    buscar_evidencias_cientificas,
    formatar_contexto_cientifico,
)


def test_extrair_data_publicacao_valida():
    d = _extrair_data_publicacao("2021-06-15T10:30:00+00:00")
    assert d == date(2021, 6, 15)


def test_extrair_data_publicacao_invalida_ou_nula():
    assert _extrair_data_publicacao(None) == date(2020, 1, 1)
    assert _extrair_data_publicacao("data-invalida") == date(2020, 1, 1)


def test_formatar_contexto_cientifico_vazio():
    assert "Nenhum artigo" in formatar_contexto_cientifico([])


def test_formatar_contexto_cientifico_preenchido():
    chunks = [
        {"chunk_id": "c1", "titulo": "Artigo 1", "conteudo": "Conteudo do artigo 1"},
        {"chunk_id": "c2", "titulo": "Artigo 2", "conteudo": "Conteudo do artigo 2"},
    ]
    formatado = formatar_contexto_cientifico(chunks)
    assert "[ID_CHUNK: c1]" in formatado
    assert "Artigo 1" in formatado
    assert "[ID_CHUNK: c2]" in formatado


@patch("APP.model.retriever.gerar_embedding_consulta")
@patch("APP.model.retriever.obter_supabase")
@patch("APP.model.retriever.obter_metadados_artigos")
def test_buscar_evidencias_cientificas(mock_catalogo, mock_supabase, mock_embedding):
    mock_embedding.return_value = [0.1] * 768

    client_mock = MagicMock()
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value.data = [
        {
            "chunk_id": "chunk-123",
            "article_id": "art-1",
            "titulo": "Titulo RPC",
            "conteudo": "Conteudo relevante do artigo...",
            "fonte": "SciELO",
            "similaridade": 0.85,
        }
    ]
    client_mock.rpc.return_value = rpc_mock
    mock_supabase.return_value = client_mock

    mock_catalogo.return_value = {
        "art-1": {
            "id": "art-1",
            "title": "Titulo do Artigo",
            "author": "Silva, A.",
            "published_at": "2022-03-01",
            "metadata": {"doi": "10.1590/test", "revista": "Revista Nutri"},
        }
    }

    fontes, raw_chunks = buscar_evidencias_cientificas("consulta de teste")

    assert len(fontes) == 1
    assert fontes[0].chunk_id == "chunk-123"
    assert fontes[0].authors == "Silva, A."
    assert fontes[0].doi == "10.1590/test"
    assert fontes[0].journal == "Revista Nutri"
    assert fontes[0].published_at == date(2022, 3, 1)
    assert len(raw_chunks) == 1
