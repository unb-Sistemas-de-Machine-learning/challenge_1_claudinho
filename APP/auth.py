"""Autenticacao da API.

STUB: por enquanto apenas exige a presenca do header `Authorization: Bearer <token>`,
sem validar a assinatura. A validacao real do JWT do Supabase Auth entra junto com a
integracao do Supabase — ate la, o app mobile ja consegue programar contra o formato final.
"""

from fastapi import Header

from APP.errors import ApiError


async def exigir_autenticacao(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("unauthorized", 401)

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError("unauthorized", 401)
    return token
