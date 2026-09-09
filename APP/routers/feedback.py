"""Endpoint de feedback (Docs/Production/01, secao 2.2).

O `trace_id` amarra a avaliacao a execucao exata que a gerou: prompt, chunks
recuperados e versao do modelo. E o que alimenta a triagem semanal descrita em
Docs/Production/02, secao 4.
"""

from fastapi import APIRouter, Depends, Request

from APP.auth import exigir_autenticacao
from APP.model import repositorio_feedback
from APP.observability import hash_usuario, registrar_etapa
from APP.ratelimit import LIMITE_ESCRITA, limiter
from APP.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
@limiter.limit(LIMITE_ESCRITA)
async def registrar_feedback(
    request: Request,
    feedback: FeedbackRequest,
    token: str = Depends(exigir_autenticacao),
) -> FeedbackResponse:
    usuario = hash_usuario(token)
    feedback_id = repositorio_feedback.salvar(usuario, feedback)

    registrar_etapa(
        "feedback",
        {
            "trace_id_avaliado": str(feedback.trace_id),
            "rating": feedback.rating,
            "reason": feedback.reason,
        },
    )
    return FeedbackResponse(status="registered", feedback_id=feedback_id)
