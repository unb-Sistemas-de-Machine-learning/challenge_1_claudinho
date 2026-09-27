"""Contrato do repositorio de feedback."""

import uuid
from types import SimpleNamespace

from APP.repositorios.feedback import Feedback, RepositorioEmMemoria, RepositorioSupabase

UM_FEEDBACK = Feedback(
    trace_id="7c1f2a90-3e4b-4d21-9f10-0b2a5c8e4d33", rating="down", reason="outro", comment=None
)


def test_em_memoria_guarda_e_devolve_um_id():
    repo = RepositorioEmMemoria()

    feedback_id = repo.salvar(UM_FEEDBACK)

    uuid.UUID(feedback_id)
    assert repo.registrados == [UM_FEEDBACK]


def test_em_memoria_gera_ids_diferentes():
    repo = RepositorioEmMemoria()

    assert repo.salvar(UM_FEEDBACK) != repo.salvar(UM_FEEDBACK)


def test_em_memoria_avisa_que_nao_persiste():
    """Guardar em memoria some no proximo deploy. O repositorio precisa deixar
    isso explicito para ninguem confundir com persistencia de verdade."""
    assert RepositorioEmMemoria.efemero is True


class _SupabaseFalso:
    """Registra o que seria inserido, sem banco."""

    def __init__(self):
        self.inserido = None

    def table(self, _nome):
        return self

    def insert(self, linha):
        self.inserido = linha
        return self

    def execute(self):
        return SimpleNamespace(data=[{"id": "feedback-1"}])


def test_supabase_insere_o_feedback_com_o_id_do_usuario(monkeypatch):
    """A tabela usa o user_id (sub do JWT) na FK; o hash serve so para o log."""
    falso = _SupabaseFalso()
    monkeypatch.setattr("APP.repositorios.feedback.obter_supabase", lambda: falso)

    identificador = RepositorioSupabase().salvar(UM_FEEDBACK)

    assert identificador == "feedback-1"
    assert falso.inserido["trace_id"] == UM_FEEDBACK.trace_id
    assert falso.inserido["rating"] == UM_FEEDBACK.rating
    assert "usuario_hash" not in falso.inserido
