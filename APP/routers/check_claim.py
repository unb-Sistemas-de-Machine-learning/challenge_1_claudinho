"""Endpoint principal de checagem.

Executa o pipeline RAG completo:
extracao de claim -> guardrails eticos -> recuperacao no pgvector -> geracao ancorada.
Documentado em Docs/Production/01_plataforma_e_deploy.md, secao 1.1.
"""

import base64
import binascii
import time
import uuid

from fastapi import APIRouter, Depends

from APP.auth import exigir_autenticacao
from APP.config import Settings, obter_settings
from APP.errors import ApiError
from APP.model.pipeline import executar_pipeline_de_checagem
from APP.observabilidade import adicionar_ao_log, trace_id_atual
from APP.ratelimit import LIMITE_CHECK_CLAIM, limitar
from APP.schemas import CheckClaimRequest, CheckClaimResponse

router = APIRouter(prefix="/api/v1", tags=["checagem"])


def _validar_tamanho_da_imagem(image_base64: str | None, settings: Settings) -> None:
    if image_base64 is None:
        return
    try:
        bytes_da_imagem = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ApiError("invalid_input", 400, "image_base64 nao e base64 valido") from erro

    if len(bytes_da_imagem) > settings.tamanho_maximo_imagem_bytes:
        raise ApiError("payload_too_large", 413)


# Rota sincrona (def, nao async def) de proposito: embeddings e LLM bloqueiam por
# segundos, e o FastAPI roda funcao sincrona em um threadpool. Como async, a espera
# pelo Ollama travaria o event loop e a API inteira, /health incluido.
@router.post(
    "/check-claim",
    response_model=CheckClaimResponse,
    # Na lista da rota, e nao como decorador: assim o limite roda antes da autenticacao
    # e da validacao do corpo (ver o docstring de APP/ratelimit.py).
    dependencies=[Depends(limitar(LIMITE_CHECK_CLAIM))],
)
def check_claim(
    requisicao: CheckClaimRequest,
    _usuario: str = Depends(exigir_autenticacao),
    settings: Settings = Depends(obter_settings),
) -> CheckClaimResponse:
    inicio = time.perf_counter()
    adicionar_ao_log(input=_descrever_entrada(requisicao))

    _validar_tamanho_da_imagem(requisicao.image_base64, settings)
    trace_id = trace_id_atual() or str(uuid.uuid4())
    resposta = executar_pipeline_de_checagem(requisicao, settings, 0, trace_id)
    # Medido depois do pipeline: e o tempo do LLM que se quer comparar entre provedores.
    resposta.latency_ms = int((time.perf_counter() - inicio) * 1000)

    adicionar_ao_log(
        output={
            "verdict": resposta.verdict,
            "risk_score": resposta.risk_score,
            "sources_count": len(resposta.sources),
        },
        # Sem as versoes no registro nao da para atribuir uma queda de qualidade
        # a mudanca que a causou (Docs/Production/02, secoes 2.3 e 3.1).
        generation={
            "model_version": resposta.model_version,
            "prompt_version": resposta.prompt_version,
        },
        performance={"cache_hit": resposta.cached},
    )
    return resposta


def _descrever_entrada(requisicao: CheckClaimRequest) -> dict[str, object]:
    """Descreve a entrada sem copiar o texto do usuario para o log.

    Docs/Production/02, secao 3.1: o log guarda o formato e o tamanho, nao o
    conteudo. O texto original fica so na resposta e, quando o pipeline existir,
    na alegacao canonica do bloco `nlp`.
    """
    bruto = requisicao.text or requisicao.url or requisicao.image_base64 or ""
    return {
        "input_type": requisicao.input_type,
        "raw_length": len(bruto),
        # Fixo por enquanto: o MVP e pt-BR. Vira deteccao quando houver
        # necessidade de outro idioma.
        "language": "pt-BR",
    }
