"""Registro do feedback do usuario — Docs/Production/01, secao 2.2.

E o que alimenta a triagem semanal e faz o benchmark de validacao crescer a
partir do uso real (Docs/Production/02, secao 4).
"""

from fastapi import APIRouter, Depends, status

from APP.auth import exigir_autenticacao
from APP.observabilidade import adicionar_ao_log
from APP.repositorios.feedback import (
    Feedback,
    RepositorioDeFeedback,
    obter_repositorio_de_feedback,
)
from APP.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/v1", tags=["feedback"])


# Rota sincrona (def, nao async def) de proposito: o FastAPI roda funcoes
# sincronas em um threadpool, entao o client sincrono do Supabase pode ser
# chamado aqui sem travar o event loop quando o RepositorioSupabase entrar.
@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def registrar_feedback(
    requisicao: FeedbackRequest,
    _token: str = Depends(exigir_autenticacao),
    repositorio: RepositorioDeFeedback = Depends(obter_repositorio_de_feedback),
) -> FeedbackResponse:
    feedback = Feedback(
        trace_id=str(requisicao.trace_id),
        rating=requisicao.rating,
        reason=requisicao.reason,
        comment=requisicao.comment,
    )
    feedback_id = repositorio.salvar(feedback)

    # O `comment` fica de fora do log: e texto livre e o usuario pode escrever
    # condicao clinica ali. Docs/Production/02, secao 3.1.
    adicionar_ao_log(
        feedback={
            "trace_id_avaliado": feedback.trace_id,
            "rating": feedback.rating,
            "reason": feedback.reason,
            "feedback_id": feedback_id,
            "tem_comentario": requisicao.comment is not None,
        }
    )
    return FeedbackResponse(status="registered", feedback_id=feedback_id)
