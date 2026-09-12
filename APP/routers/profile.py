"""Endpoints de perfil de saude (Docs/Production/01, secao 2.3).

O perfil e opcional: os filtros de grupo de risco (Docs/Ethics/02) so entram em
jogo quando o usuario preenche. Ver `APP/model/repositorio_perfil.py` para a nota
sobre o stub em memoria que sera substituido pela tabela `profiles` do Supabase.
"""

from fastapi import APIRouter, Depends

from APP.auth import exigir_autenticacao
from APP.errors import ApiError
from APP.model import repositorio_perfil
from APP.observability import hash_usuario, registrar_etapa
from APP.schemas import Profile

router = APIRouter(prefix="/api/v1", tags=["perfil"])


@router.get("/profile", response_model=Profile)
async def obter_perfil(token: str = Depends(exigir_autenticacao)) -> Profile:
    perfil = repositorio_perfil.buscar(hash_usuario(token))
    if perfil is None:
        raise ApiError("profile_not_found", 404)
    return perfil


@router.put("/profile", response_model=Profile)
async def atualizar_perfil(
    perfil: Profile,
    token: str = Depends(exigir_autenticacao),
) -> Profile:
    salvo = repositorio_perfil.salvar(hash_usuario(token), perfil)
    # Docs/Production/02, secao 3.1: so o booleano, nunca a condicao clinica em si.
    registrar_etapa("profile", {"has_conditions": bool(salvo.conditions)})
    return salvo
