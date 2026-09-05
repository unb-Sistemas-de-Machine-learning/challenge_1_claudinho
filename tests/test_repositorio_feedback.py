"""Contrato do repositorio de feedback."""

import uuid

import pytest

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


def test_supabase_avisa_claramente_que_falta_a_tabela():
    """Enquanto a tabela nao existir, falhar com uma mensagem util e melhor do
    que devolver 201 mentindo que guardou."""
    with pytest.raises(NotImplementedError) as erro:
        RepositorioSupabase().salvar(UM_FEEDBACK)

    assert "feedback" in str(erro.value).lower()
