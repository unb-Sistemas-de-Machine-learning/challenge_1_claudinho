"""Persistencia do feedback do usuario.

Docs/Production/02, secao 8: "Criar a tabela `feedback` no Supabase, alinhada
com a frente de Dados." Essa tabela ainda NAO existe — o schema em
Docs/Data/02_armazenamento_e_estrutura.md so tem `sources`, `training_data` e
`chunks`.

Por isso o acesso ao banco fica atras de uma interface: o endpoint ja funciona
e ja valida o contrato hoje, guardando em memoria, e trocar para o Supabase
depois e mudar uma linha (ver `obter_repositorio_de_feedback` no fim do arquivo).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from APP.config import obter_settings
from APP.model.database import obter_supabase


@dataclass(frozen=True)
class Feedback:
    """Uma avaliacao do usuario sobre uma resposta.

    `trace_id` e a amarra com a execucao exata que gerou a resposta avaliada:
    qual prompt, quais chunks, qual versao de modelo. Sem ele o feedback nao
    serve para a triagem semanal descrita na secao 4 do Production/02.
    """

    trace_id: str
    rating: str
    # Hash para o log; `usuario` e o id de verdade (sub do JWT), que a tabela usa na FK.
    usuario_hash: str | None = None
    usuario: str | None = None
    reason: str | None = None
    comment: str | None = None
    criado_em: datetime = field(default_factory=lambda: datetime.now(UTC))


class RepositorioDeFeedback(Protocol):
    def salvar(self, feedback: Feedback) -> str:
        """Persiste o feedback e devolve o id gerado."""
        ...


class RepositorioEmMemoria:
    """Implementacao atual: guarda em uma lista dentro do processo.

    Serve para o endpoint existir e ser testavel enquanto a tabela nao chega.
    NAO e persistencia: some quando o processo reinicia, e cada instancia da API
    tem a sua propria lista. Nunca use isso valendo em producao.
    """

    efemero = True

    def __init__(self) -> None:
        self.registrados: list[Feedback] = []

    def salvar(self, feedback: Feedback) -> str:
        self.registrados.append(feedback)
        return str(uuid.uuid4())

    def limpar(self) -> None:
        """Usado pelos testes para isolar um caso do outro."""
        self.registrados.clear()


class RepositorioSupabase:
    """Feedback na tabela `feedback` (deploy/sql/001_profiles_e_feedback.sql).

    A rota e sincrona de proposito (ver APP/routers/feedback.py), entao o client sincrono
    do Supabase nao trava o event loop.
    """

    TABELA = "feedback"

    def salvar(self, feedback: Feedback) -> str:
        resposta = (
            obter_supabase()
            .table(self.TABELA)
            .insert(
                {
                    "trace_id": feedback.trace_id,
                    "user_id": feedback.usuario,
                    "rating": feedback.rating,
                    "reason": feedback.reason,
                    "comment": feedback.comment,
                }
            )
            .execute()
        )
        return resposta.data[0]["id"]


# Instancia unica do repositorio em memoria: sem isso cada requisicao criaria
# uma lista nova e o feedback anterior sumiria dentro do mesmo processo.
_repositorio_em_memoria = RepositorioEmMemoria()
_repositorio_supabase = RepositorioSupabase()


def obter_repositorio_de_feedback() -> RepositorioDeFeedback:
    """Dependencia do FastAPI que entrega o repositorio em uso.

    Escolhido por configuracao (REPOSITORIOS): "supabase" em producao, depois de rodar
    deploy/sql/001_profiles_e_feedback.sql; "memoria" no desenvolvimento e nos testes.
    E o unico ponto do codigo que muda — a rota nao sabe (nem precisa saber) onde o
    feedback e guardado.
    """
    if obter_settings().repositorios == "supabase":
        return _repositorio_supabase
    return _repositorio_em_memoria
