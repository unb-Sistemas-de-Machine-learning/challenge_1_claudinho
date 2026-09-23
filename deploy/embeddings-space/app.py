"""Servico de embeddings do Claudinho (Hugging Face Spaces, SDK Docker).

Tira o modelo de embeddings de dentro da API: a API chama este servico e deixa de
precisar do torch, cabendo na Vercel e no Render gratuito. Usa o mesmo modelo com que a
base foi indexada, entao os vetores sao compativeis e nao ha reindexacao.

Contrato (o mesmo que APP/model/embeddings.py espera):
    POST /embed   {"textos": ["query: ..."]}  ->  {"modelo", "dimensao", "vetores": [[...]]}
    GET  /health
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

MODELO = os.environ.get("MODELO_EMBEDDINGS", "intfloat/multilingual-e5-base")
_estado: dict = {}


def carregar_modelo():
    # Import aqui dentro para os testes da API poderem exercitar o contrato sem o torch.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODELO)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    # Carrega na subida, nao na primeira requisicao: a primeira checagem do dia nao
    # precisa esperar o modelo inteiro ser lido do disco.
    # Nao usar setdefault: ele avaliaria carregar_modelo() mesmo com o modelo ja carregado.
    if "modelo" not in _estado:
        _estado["modelo"] = carregar_modelo()
    yield


app = FastAPI(title="Claudinho - embeddings", lifespan=ciclo_de_vida)


class Pedido(BaseModel):
    # Limites contra abuso: a API manda um texto por consulta.
    textos: list[str] = Field(min_length=1, max_length=32)


@app.post("/embed")
def embed(pedido: Pedido) -> dict:
    textos = [t[:2000] for t in pedido.textos]
    vetores = _estado["modelo"].encode(textos, normalize_embeddings=True).tolist()
    return {"modelo": MODELO, "dimensao": len(vetores[0]), "vetores": vetores}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "modelo": MODELO, "carregado": "modelo" in _estado}
