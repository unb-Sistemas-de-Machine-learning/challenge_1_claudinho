"""Extracao rapida da alegacao (issue #26).

A tela de carregamento mostra "Entendi assim: ..." enquanto a checagem roda, para a
pessoa ver que foi compreendida antes de a resposta chegar (Docs/User/02, secao 2.4).
O `canonical_claim` do /check-claim nao serve: ele chega junto da resposta, quando a
espera ja acabou.

Aqui nao ha LLM, embedding nem banco: so as regras de APP/model/claim_extractor.py, que
respondem em milissegundos. Por isso o limite e o de escrita, e nao o da checagem: gastar
a cota de checagem com esta chamada tiraria checagens de verdade da pessoa.
"""

from fastapi import APIRouter, Depends

from APP.auth import exigir_autenticacao
from APP.model.claim_extractor import checar_recusa_segura, reformular_pergunta_amigavel
from APP.observabilidade import adicionar_ao_log
from APP.ratelimit import LIMITE_ESCRITA, limitar
from APP.schemas import ExtractClaimRequest, ExtractClaimResponse

router = APIRouter(prefix="/api/v1", tags=["checagem"])


@router.post(
    "/extract-claim",
    response_model=ExtractClaimResponse,
    dependencies=[Depends(limitar(LIMITE_ESCRITA))],
)
def extract_claim(
    requisicao: ExtractClaimRequest,
    _usuario: str = Depends(exigir_autenticacao),
) -> ExtractClaimResponse:
    acionou_guardrail, _mensagem = checar_recusa_segura(requisicao.text)

    adicionar_ao_log(
        # Comprimento, nunca o texto: a duvida pode conter dado de saude.
        input={"raw_length": len(requisicao.text)},
        guardrails={"safe_refusal": acionou_guardrail},
    )
    return ExtractClaimResponse(
        canonical_claim=reformular_pergunta_amigavel(requisicao.text),
        # A tela usa isto para nao prometer "procurando nos estudos" quando a checagem vai
        # terminar numa resposta de cuidado.
        safe_refusal=acionou_guardrail,
    )
