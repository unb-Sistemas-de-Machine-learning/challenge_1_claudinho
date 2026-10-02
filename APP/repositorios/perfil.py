"""Persistencia do perfil de saude.

Mesma estrutura do `APP/repositorios/feedback.py`, e pelo mesmo motivo: a tabela
`profiles` ainda NAO existe no Supabase (o schema em Docs/Data/02_armazenamento_e_estrutura.md
tem `sources`, `training_data` e `chunks`). O acesso fica atras de uma interface para
que a rota ja funcione hoje, guardando em memoria, e a troca depois seja em um lugar so.

O consentimento da LGPD NAO e checado aqui de proposito: quem recusa perfil com condicao
clinica sem `consent_health_data` e o validador do `Profile` em APP/schemas.py, antes do
dado chegar neste modulo. Duplicar a regra daria a impressao de duas travas quando existe
uma so, e a copia daqui nunca teria como ser exercitada por teste.
"""

from typing import Protocol

from APP.config import obter_settings
from APP.model.database import obter_supabase
from APP.schemas import Profile


class RepositorioDePerfil(Protocol):
    def salvar(self, usuario_hash: str, perfil: Profile) -> Profile:
        """Cria ou substitui o perfil do usuario e devolve o que ficou gravado."""
        ...

    def buscar(self, usuario_hash: str) -> Profile | None:
        """Devolve o perfil do usuario, ou None se ele ainda nao preencheu."""
        ...

    def apagar(self, usuario_hash: str) -> bool:
        """Apaga o perfil. Devolve False quando nao havia nada para apagar.

        Exigido por docs/Ethics/02, secao 4: a pessoa pode pedir a exclusao imediata dos
        dados de saude a qualquer momento.
        """
        ...


class RepositorioEmMemoria:
    """Implementacao atual: um dicionario dentro do processo.

    NAO e persistencia: some quando o processo reinicia, e cada instancia da API tem o
    seu proprio dicionario. Na pratica o usuario perde o perfil a cada deploy. Serve
    enquanto o alvo e demo local e a tabela nao existe.
    """

    efemero = True

    def __init__(self) -> None:
        self.perfis: dict[str, Profile] = {}

    def salvar(self, usuario_hash: str, perfil: Profile) -> Profile:
        self.perfis[usuario_hash] = perfil
        return perfil

    def buscar(self, usuario_hash: str) -> Profile | None:
        return self.perfis.get(usuario_hash)

    def apagar(self, usuario_hash: str) -> bool:
        return self.perfis.pop(usuario_hash, None) is not None

    def limpar(self) -> None:
        """Usado pelos testes para isolar um caso do outro."""
        self.perfis.clear()


class RepositorioSupabase:
    """Perfil na tabela `profiles` (deploy/sql/001_profiles_e_feedback.sql).

    Indexado pelo `user_id` (o `sub` do JWT), e nao pelo hash: o hash serve para o log,
    a tabela usa a chave de verdade, com RLS e FK para auth.users.
    """

    TABELA = "profiles"

    def salvar(self, usuario: str, perfil: Profile) -> Profile:
        linha = perfil.model_dump(mode="json") | {"user_id": usuario}
        obter_supabase().table(self.TABELA).upsert(linha, on_conflict="user_id").execute()
        return perfil

    def buscar(self, usuario: str) -> Profile | None:
        resposta = (
            obter_supabase()
            .table(self.TABELA)
            .select("*")
            .eq("user_id", usuario)
            .limit(1)
            .execute()
        )
        if not resposta.data:
            return None
        linha = {c: v for c, v in resposta.data[0].items() if c in Profile.model_fields}
        return Profile(**linha)
<<<<<<< HEAD
=======

    def apagar(self, usuario: str) -> bool:
        resposta = obter_supabase().table(self.TABELA).delete().eq("user_id", usuario).execute()
        return bool(resposta.data)
>>>>>>> 7b7f04102db713aa0caa89ac646f186adb9631ca


# Instancia unica: sem isso cada requisicao criaria um dicionario novo e o perfil
# salvo sumiria dentro do mesmo processo.
_repositorio_em_memoria = RepositorioEmMemoria()


_repositorio_supabase = RepositorioSupabase()


def obter_repositorio_de_perfil() -> RepositorioDePerfil:
    """Dependencia do FastAPI que entrega o repositorio em uso.

    Escolhido por configuracao (REPOSITORIOS): "supabase" em producao, depois de rodar
    deploy/sql/001_profiles_e_feedback.sql; "memoria" no desenvolvimento e nos testes.
    Em memoria o perfil nao sobrevive a troca de instancia da Vercel.
    """
    if obter_settings().repositorios == "supabase":
        return _repositorio_supabase
    return _repositorio_em_memoria
