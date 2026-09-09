"""Persistencia de feedback (Docs/Production/01, secao 2.2).

STUB EM MEMORIA, no mesmo espirito de `repositorio_perfil.py`: a interface fica
congelada para as rotas, e a substituicao pela tabela `feedback` do Supabase
(Docs/Production/02, secao 4) acontece so aqui.
"""

from uuid import uuid4

from APP.schemas import FeedbackRequest

_feedbacks: dict[str, dict] = {}


def salvar(usuario_hash: str, feedback: FeedbackRequest) -> str:
    feedback_id = str(uuid4())
    _feedbacks[feedback_id] = {"usuario_hash": usuario_hash, **feedback.model_dump()}
    return feedback_id


def limpar() -> None:
    """Usado pelos testes para isolar um caso do outro."""
    _feedbacks.clear()
