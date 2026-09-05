"""Endpoint principal de checagem.

ATENCAO: a resposta ainda e MOCKADA. O objetivo deste modulo hoje e congelar o
contrato para o app mobile. O pipeline real (cache semantico -> extracao de claim ->
recuperacao no pgvector -> geracao ancorada -> guardrails) descrito em
Docs/Production/01, secao 1.1, substitui o corpo de `montar_resposta_mockada`.
"""

import base64
import binascii
import time
import uuid

from fastapi import APIRouter, Depends

from APP.auth import exigir_autenticacao
from APP.config import Settings, obter_settings
from APP.errors import ApiError
from APP.observabilidade import adicionar_ao_log, trace_id_atual
from APP.schemas import CheckClaimRequest, CheckClaimResponse, Fonte
from APP.verdict import classificar_veredito

router = APIRouter(prefix="/api/v1", tags=["checagem"])

MODEL_VERSION_MOCK = "mock@0.1.0"
PROMPT_VERSION_MOCK = "mock-v0"
RISK_SCORE_MOCK = 0.78

DISCLAIMER = (
    "Esta informacao nao substitui a consulta com um nutricionista ou medico. "
    "Texto provisorio: a redacao final sera definida pela frente de Etica "
    "(Docs/Ethics/03_transparencia_e_disclaimers.md)."
)


def _validar_tamanho_da_imagem(image_base64: str | None, settings: Settings) -> None:
    if image_base64 is None:
        return
    try:
        bytes_da_imagem = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as erro:
        raise ApiError("invalid_input", 400, "image_base64 nao e base64 valido") from erro

    if len(bytes_da_imagem) > settings.tamanho_maximo_imagem_bytes:
        raise ApiError("payload_too_large", 413)


def montar_resposta_mockada(requisicao: CheckClaimRequest, latency_ms: int) -> CheckClaimResponse:
    return CheckClaimResponse(
        # O trace_id vem do middleware de log, para a resposta e o registro
        # apontarem para a mesma execucao. O uuid4 aqui e so a rede de seguranca
        # de quando a rota e chamada fora do ciclo de requisicao (testes unitarios).
        trace_id=trace_id_atual() or str(uuid.uuid4()),
        canonical_claim=(
            "O consumo de agua com limao em jejum possui efeito termogenico ou de "
            "reducao de retencao hidrica?"
        ),
        verdict=classificar_veredito(RISK_SCORE_MOCK),
        risk_score=RISK_SCORE_MOCK,
        risk_level="baixo",
        answer=(
            "Nao ha evidencia de que agua com limao acelere a queima de gordura. O efeito "
            "de 'desinchar' relatado costuma vir da hidratacao em si [Ref: chunk_a1f2]. "
            "(RESPOSTA MOCKADA — o pipeline de RAG ainda nao esta ligado.)"
        ),
        sources=[
            Fonte(
                chunk_id="chunk_a1f2",
                title="Efeitos metabolicos de compostos citricos: revisao sistematica",
                authors="Silva, R.; Almeida, C.",
                journal="Revista de Nutricao",
                published_at="2021-06-01",
                doi="10.1590/xxxx-xxxx",
                excerpt="Nao foram observadas diferencas significativas no gasto energetico...",
            )
        ],
        disclaimer=DISCLAIMER,
        cached=False,
        latency_ms=latency_ms,
        model_version=MODEL_VERSION_MOCK,
        prompt_version=PROMPT_VERSION_MOCK,
    )


@router.post("/check-claim", response_model=CheckClaimResponse)
async def check_claim(
    requisicao: CheckClaimRequest,
    _token: str = Depends(exigir_autenticacao),
    settings: Settings = Depends(obter_settings),
) -> CheckClaimResponse:
    inicio = time.perf_counter()
    adicionar_ao_log(input=_descrever_entrada(requisicao))

    _validar_tamanho_da_imagem(requisicao.image_base64, settings)
    decorrido_ms = int((time.perf_counter() - inicio) * 1000)
    resposta = montar_resposta_mockada(requisicao, decorrido_ms)

    adicionar_ao_log(
        output={
            "verdict": resposta.verdict,
            "risk_score": resposta.risk_score,
            "sources_count": len(resposta.sources),
        },
        # Sem as versoes no registro nao da para atribuir uma queda de qualidade
        # a mudanca que a causou (Docs/Production/02, secoes 2.3 e 3.1).
        # input_tokens, output_tokens e cost_usd entram quando houver LLM de fato.
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
