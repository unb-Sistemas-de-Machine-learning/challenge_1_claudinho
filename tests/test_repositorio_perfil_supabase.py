"""Perfil guardado no Supabase (issues #19 e #22 do front).

Em memoria, o perfil some quando a Vercel troca de instancia: o usuario preenche e, na
requisicao seguinte, ele nao existe mais.
"""

from types import SimpleNamespace

import pytest

from APP.config import obter_settings
from APP.repositorios.perfil import (
    RepositorioEmMemoria,
    RepositorioSupabase,
    obter_repositorio_de_perfil,
)
from APP.schemas import Profile

PERFIL = Profile(sex="F", height_cm=165, conditions=["diabetes_tipo_2"], consent_health_data=True)
USUARIO = "8f14e45f-ceea-467a-9f0a-1b2c3d4e5f60"


class _SupabaseFalso:
    def __init__(self, linhas=None):
        self.linhas = linhas or []
        self.upsert_recebido = None

    def table(self, _nome):
        return self

    def upsert(self, linha, on_conflict=None):
        self.upsert_recebido = (linha, on_conflict)
        return self

    def select(self, _colunas):
        return self

    def eq(self, coluna, valor):
        self.filtro = (coluna, valor)
        return self

    def limit(self, _n):
        return self

    def execute(self):
        return SimpleNamespace(data=self.linhas)


@pytest.fixture
def supabase(monkeypatch):
    falso = _SupabaseFalso()
    monkeypatch.setattr("APP.repositorios.perfil.obter_supabase", lambda: falso)
    return falso


def test_salvar_usa_o_id_do_usuario_como_chave(supabase):
    """A tabela indexa pelo user_id (sub do JWT), com FK e RLS; o hash serve so para o log."""
    RepositorioSupabase().salvar(USUARIO, PERFIL)

    linha, conflito = supabase.upsert_recebido
    assert linha["user_id"] == USUARIO
    assert linha["conditions"] == ["diabetes_tipo_2"]
    assert conflito == "user_id"


def test_buscar_devolve_none_quando_nao_ha_perfil(supabase):
    assert RepositorioSupabase().buscar(USUARIO) is None


def test_buscar_ignora_colunas_que_o_contrato_nao_tem(supabase):
    """A tabela tem updated_at e user_id, que nao existem no Profile do contrato."""
    supabase.linhas = [
        {
            "user_id": USUARIO,
            "sex": "F",
            "height_cm": 165,
            "conditions": ["diabetes_tipo_2"],
            "consent_health_data": True,
            "updated_at": "2026-09-27T12:00:00Z",
        }
    ]

    perfil = RepositorioSupabase().buscar(USUARIO)

    assert perfil.sex == "F"
    assert perfil.conditions == ["diabetes_tipo_2"]


@pytest.mark.parametrize(
    ("configurado", "esperado"),
    [("memoria", RepositorioEmMemoria), ("supabase", RepositorioSupabase)],
)
def test_configuracao_escolhe_onde_guardar(monkeypatch, configurado, esperado):
    monkeypatch.setenv("REPOSITORIOS", configurado)
    obter_settings.cache_clear()

    assert isinstance(obter_repositorio_de_perfil(), esperado)

    obter_settings.cache_clear()
