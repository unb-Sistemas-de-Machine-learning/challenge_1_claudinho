"""Embeddings de consulta com intfloat/multilingual-e5-base (768 dimensoes).

Documentado em Docs/Model/02_arquitetura_nlp_rag.md e Docs/Data/02_armazenamento_e_estrutura.md.

Dois modos, escolhidos pela configuracao:

- **Remoto** (`EMBEDDINGS_URL` definida): e o modo de producao. A API nao carrega o modelo
  nem importa o torch, entao fica leve o bastante para a Vercel (limite de 500 MB por
  funcao) e para o Render gratuito (512 MB). Dois provedores:
  - `hf-inference` (padrao): a API de inferencia do Hugging Face roda o modelo. Nao exige
    Space nem conta paga, mas conta gratuita tem cota mensal pequena e sem excedente: se
    acabar, as chamadas param ate o mes virar.
  - `space`: o servico proprio de deploy/embeddings-space (criar Space Docker exige PRO).
- **Local** (sem `EMBEDDINGS_URL`): carrega o modelo no proprio processo. So para
  desenvolvimento; exige `requirements-ml.txt`.

Os dois usam o MESMO modelo: trocar de modelo mudaria os vetores e obrigaria a reindexar
a base inteira no pgvector.
"""

from functools import lru_cache

import httpx

from APP.config import obter_settings

MODELO_PADRAO = "intfloat/multilingual-e5-base"
DIMENSAO = 768
PREFIXO_CONSULTA = "query: "


class EmbeddingsIndisponiveis(RuntimeError):
    """O servico remoto falhou ou devolveu um vetor incompativel com a base."""


def gerar_embedding_consulta(texto: str) -> list[float]:
    """Gera o embedding normalizado de uma consulta de busca.

    O e5 exige o prefixo 'query: ' para consultas em busca assimetrica.
    """
    texto_limpo = texto.strip()
    formatado = (
        texto_limpo
        if texto_limpo.startswith(PREFIXO_CONSULTA)
        else (f"{PREFIXO_CONSULTA}{texto_limpo}")
    )

    settings = obter_settings()
    if settings.embeddings_url:
        vetor = _remoto(formatado, settings)
    else:
        vetor = _local(formatado)

    if len(vetor) != DIMENSAO:
        # Vetor de outra dimensao quebraria a busca no pgvector com um erro pouco claro.
        raise EmbeddingsIndisponiveis(f"vetor com {len(vetor)} dimensoes, esperado {DIMENSAO}")
    return vetor


def _remoto(texto: str, settings) -> list[float]:
    cabecalhos = {}
    if settings.embeddings_token:
        cabecalhos["Authorization"] = f"Bearer {settings.embeddings_token}"

    if settings.embeddings_provedor == "space":
        url = f"{settings.embeddings_url.rstrip('/')}/embed"
        corpo = {"textos": [texto]}
    else:
        # A URL ja e a do pipeline: .../models/<modelo>/pipeline/feature-extraction
        url = settings.embeddings_url
        corpo = {"inputs": texto, "normalize": True}

    try:
        with httpx.Client(timeout=settings.embeddings_timeout_s) as cliente:
            resposta = cliente.post(url, json=corpo, headers=cabecalhos)
            resposta.raise_for_status()
            dados = resposta.json()
    except httpx.HTTPStatusError as erro:
        # 402 = cota mensal do Hugging Face esgotada; 401/403 = token sem permissao.
        # O codigo vai para o log; a URL nao, porque pode carregar dados da requisicao.
        raise EmbeddingsIndisponiveis(f"HTTP {erro.response.status_code}") from erro
    except (httpx.HTTPError, ValueError) as erro:
        raise EmbeddingsIndisponiveis(type(erro).__name__) from erro

    try:
        vetor = dados["vetores"][0] if settings.embeddings_provedor == "space" else dados
        # O hf-inference devolve [..768..] para um texto, ou [[..768..]] em algumas versoes.
        # Cuidado: se o endpoint devolver a matriz TOKEN A TOKEN, cada linha tambem tem 768
        # posicoes, entao pegar a linha 0 passaria pela checagem de dimensao e a busca
        # passaria a usar o embedding do primeiro token, sem erro e sem log. Uma linha so
        # e um lote de um texto; varias linhas para um texto so sao tokens.
        if vetor and isinstance(vetor[0], list):
            if len(vetor) > 1:
                raise EmbeddingsIndisponiveis(
                    f"resposta com {len(vetor)} vetores para um texto: matriz por token?"
                )
            vetor = vetor[0]
        return [float(x) for x in vetor]
    except (KeyError, IndexError, TypeError, ValueError) as erro:
        raise EmbeddingsIndisponiveis(f"resposta inesperada: {type(erro).__name__}") from erro


def _local(texto: str) -> list[float]:
    return obter_modelo_embeddings().encode(texto, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def obter_modelo_embeddings(nome_modelo: str = MODELO_PADRAO):
    """Carrega o modelo local uma unica vez.

    Import dentro da funcao, de proposito: no modo remoto o sentence-transformers nem
    precisa estar instalado, e importar no topo do modulo puxaria o torch para a API.
    """
    import huggingface_hub.utils.logging as hf_logging
    from sentence_transformers import SentenceTransformer

    hf_logging.set_verbosity_error()
    return SentenceTransformer(nome_modelo)
