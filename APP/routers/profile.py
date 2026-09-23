"""Perfil de saude do usuario - Docs/Production/01, secao 2.3.

O perfil e opcional: os filtros de grupo de risco (Docs/Ethics/02) so entram em jogo
quando o usuario preenche. E o `use_profile` do /check-claim permite desligar o perfil
em uma consulta pontual, sem apagar nada.
"""

from datetime import date

from fastapi import APIRouter, Depends, status

from APP.auth import exigir_autenticacao
from APP.errors import ApiError
from APP.model import disclaimers
from APP.observabilidade import adicionar_ao_log, hash_de_usuario
from APP.ratelimit import LIMITE_ESCRITA, limitar
from APP.repositorios.perfil import RepositorioDePerfil, obter_repositorio_de_perfil
from APP.schemas import Profile

router = APIRouter(prefix="/api/v1", tags=["perfil"])


@router.get(
    "/profile",
    response_model=Profile,
    dependencies=[Depends(limitar(LIMITE_ESCRITA))],
)
def obter_perfil(
    usuario: str = Depends(exigir_autenticacao),
    repositorio: RepositorioDePerfil = Depends(obter_repositorio_de_perfil),
) -> Profile:
    perfil = repositorio.buscar(hash_de_usuario(usuario))
    if perfil is None:
        # 404 e nao 200 com corpo vazio: "ainda nao preencheu" e diferente de
        # "preencheu e esta tudo em branco", e o app trata os dois casos de formas
        # diferentes (convite para preencher x formulario vazio).
        raise ApiError("profile_not_found", 404)
    return perfil


@router.put(
    "/profile",
    response_model=Profile,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(limitar(LIMITE_ESCRITA))],
)
def atualizar_perfil(
    perfil: Profile,
    usuario: str = Depends(exigir_autenticacao),
    repositorio: RepositorioDePerfil = Depends(obter_repositorio_de_perfil),
) -> Profile:
    """Cria ou substitui o perfil inteiro.

    Substitui e nao mescla: com mescla, remover uma condicao clinica exigiria um verbo
    proprio, e o app precisa de um caminho simples para o usuario tirar algo do perfil.
    """
    # Docs/Ethics/02: perfil com menos de 18 anos bloqueia o uso (LGPD Art. 14). Recusar
    # aqui tambem impede que dado de saude de menor chegue a ser guardado.
    if perfil.birth_date and _idade(perfil.birth_date) < disclaimers.IDADE_MINIMA:
        raise ApiError("age_restricted", 403, disclaimers.MENOR_DE_IDADE)

    salvo = repositorio.salvar(hash_de_usuario(usuario), perfil)

    # Docs/Production/02, secao 3.1: so os booleanos, nunca a condicao clinica em si.
    adicionar_ao_log(
        profile={
            "has_conditions": bool(salvo.conditions),
            "has_restrictions": bool(salvo.dietary_restrictions),
            "consent_health_data": salvo.consent_health_data,
        }
    )
    return salvo


def _idade(nascimento: date, hoje: date | None = None) -> int:
    hoje = hoje or date.today()
    fez_aniversario = (hoje.month, hoje.day) >= (nascimento.month, nascimento.day)
    return hoje.year - nascimento.year - (0 if fez_aniversario else 1)
