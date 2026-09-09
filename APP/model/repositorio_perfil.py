"""Persistencia de perfil de saude.

STUB EM MEMORIA. O modelo de dados e o schema da tabela `profiles` sao da frente de
Dados (Docs/Data/01_tipos_e_fontes_de_dados.md). Este arquivo existe apenas para que
as rotas ja tenham a interface final: quando o schema do Supabase for definido, a
substituicao acontece so aqui.

Consequencia de ser em memoria: os dados somem quando o processo reinicia e nao sao
compartilhados entre instancias. Aceitavel enquanto o alvo e demo local.
"""

from APP.schemas import Profile

_perfis: dict[str, Profile] = {}


def salvar(usuario_hash: str, perfil: Profile) -> Profile:
    if not perfil.consent_health_data:
        # Sem consentimento, condicoes clinicas nao podem ser persistidas (LGPD Art. 5o, II).
        perfil = perfil.model_copy(update={"conditions": []})
    _perfis[usuario_hash] = perfil
    return perfil


def buscar(usuario_hash: str) -> Profile | None:
    return _perfis.get(usuario_hash)


def limpar() -> None:
    """Usado pelos testes para isolar um caso do outro."""
    _perfis.clear()
