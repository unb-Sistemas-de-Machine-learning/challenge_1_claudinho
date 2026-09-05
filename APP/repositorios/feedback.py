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


@dataclass(frozen=True)
class Feedback:
    """Uma avaliacao do usuario sobre uma resposta.

    `trace_id` e a amarra com a execucao exata que gerou a resposta avaliada:
    qual prompt, quais chunks, qual versao de modelo. Sem ele o feedback nao
    serve para a triagem semanal descrita na secao 4 do Production/02.
    """

    trace_id: str
    rating: str
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


class RepositorioSupabase:
    """Implementacao definitiva — falta a tabela.

    ------------------------------------------------------------------
    O QUE FAZER PARA LIGAR ISSO (na ordem):
    ------------------------------------------------------------------

    1) Combinar o schema com a frente de Dados (Beatriz). A tabela `feedback`
       nao esta no Docs/Data/02, entao ela precisa ser adicionada la tambem —
       o documento e a fonte da verdade do banco, nao este arquivo.

       Sugestao de ponto de partida, derivada do contrato da secao 2.2 do
       Production/01 e do que a triagem da secao 4 do Production/02 precisa:

           create table feedback (
             id           uuid primary key default gen_random_uuid(),
             trace_id     uuid not null,
             user_id      uuid references auth.users(id),
             rating       text not null check (rating in ('up','down')),
             reason       text check (reason in (
                            'fonte_irrelevante','resposta_confusa','parece_errado',
                            'tom_julgador','nao_respondeu','outro')),
             comment      text,
             created_at   timestamptz not null default now(),
             triaged_at   timestamptz,          -- preenchido na triagem semanal
             triage_notes text
           );
           create index on feedback (created_at desc);
           create index on feedback (rating, reason);

       Dois pontos que valem discussao com a Beatriz e a Maria Clara antes de
       rodar isso:

       - `trace_id` deveria ser FK? Hoje nao ha tabela de execucoes: o trace vive
         no log estruturado e no Langfuse. Enquanto for assim, deixe sem FK, ou
         o insert vai falhar para todo trace que nao esteja no banco.
       - `comment` e texto livre e o usuario pode escrever condicao clinica ali
         ("tenho diabetes e..."). Isso torna a coluna dado sensivel de LGPD,
         igual ao perfil de saude. Vale decidir se guarda, se guarda com prazo
         de expurgo, ou se so guarda o motivo estruturado.

    2) Habilitar RLS na tabela, senao qualquer usuario autenticado le o feedback
       dos outros. O minimo: insert liberado para authenticated, select apenas
       para o time.

    3) Implementar o `salvar` abaixo, mais ou menos assim:

           from APP.model.database import obter_supabase

           def salvar(self, feedback: Feedback) -> str:
               resposta = (
                   obter_supabase()
                   .table("feedback")
                   .insert({
                       "trace_id": feedback.trace_id,
                       "rating": feedback.rating,
                       "reason": feedback.reason,
                       "comment": feedback.comment,
                   })
                   .execute()
               )
               return resposta.data[0]["id"]

       A rota e sincrona de proposito (ver APP/routers/feedback.py), entao dar
       para usar o client sincrono do Supabase sem travar o event loop.

    4) Trocar a implementacao em `obter_repositorio_de_feedback`, no fim deste
       arquivo, e apagar este aviso.
    """

    def salvar(self, feedback: Feedback) -> str:
        raise NotImplementedError(
            "A tabela `feedback` ainda nao existe no Supabase. "
            "Veja o passo a passo no docstring de RepositorioSupabase "
            "(APP/repositorios/feedback.py)."
        )


# Instancia unica do repositorio em memoria: sem isso cada requisicao criaria
# uma lista nova e o feedback anterior sumiria dentro do mesmo processo.
_repositorio_em_memoria = RepositorioEmMemoria()


def obter_repositorio_de_feedback() -> RepositorioDeFeedback:
    """Dependencia do FastAPI que entrega o repositorio em uso.

    QUANDO A TABELA EXISTIR: troque o retorno por `RepositorioSupabase()`.
    E o unico ponto do codigo que precisa mudar — a rota nao sabe (nem precisa
    saber) onde o feedback e guardado.
    """
    return _repositorio_em_memoria
