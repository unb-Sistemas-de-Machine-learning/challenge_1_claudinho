"""Autenticacao da API: validacao do JWT emitido pelo Supabase Auth.

Dois modos, decididos pela configuracao:

- **Producao/staging**: exige `SUPABASE_JWT_SECRET` e valida assinatura, expiracao e
  audiencia do token. Devolve o `sub` (id do usuario no Supabase).
- **Local**: sem o segredo configurado, aceita qualquer token nao vazio e o devolve
  como identidade. Serve para desenvolvimento e para a suite de testes.

O modo local NUNCA vale fora de `APP_ENV=local`: `verificar_configuracao` roda na subida
da aplicacao e derruba o processo se o segredo faltar. Sem essa trava, um deploy com a
variavel esquecida subiria com a autenticacao efetivamente desligada — e o sistema guarda
dado de saude.
"""

import jwt
from fastapi import Depends, Header

from APP.config import Settings, obter_settings
from APP.errors import ApiError

# O Supabase Auth emite tokens HS256 com esta audiencia para usuarios logados.
ALGORITMO = "HS256"
AUDIENCIA = "authenticated"


def verificar_configuracao(settings: Settings) -> None:
    """Falha rapido na subida se a autenticacao estiver desligada fora do local."""
    if settings.app_env != "local" and not settings.supabase_jwt_secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET e obrigatorio quando APP_ENV != 'local'. "
            "Sem ele a API aceitaria qualquer token."
        )


async def exigir_autenticacao(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(obter_settings),
) -> str:
    """Devolve a identidade do usuario: o `sub` do JWT, ou o proprio token no modo local.

    A identidade precisa ser ESTAVEL entre sessoes — e ela que indexa o perfil de saude.
    Usar o token cru daria um id novo a cada login, e o perfil do usuario simplesmente
    desapareceria depois de sair e entrar de novo.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError("unauthorized", 401)

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError("unauthorized", 401)

    if not settings.supabase_jwt_secret:
        return token  # modo local

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[ALGORITMO],
            audience=AUDIENCIA,
        )
    except jwt.ExpiredSignatureError:
        raise ApiError("unauthorized", 401, "token expirado") from None
    except jwt.InvalidTokenError:
        # Assinatura invalida, audiencia errada, formato quebrado: a causa exata nao volta
        # para o cliente, ela so ajudaria quem esta tentando forjar um token.
        raise ApiError("unauthorized", 401, "token invalido") from None

    usuario = payload.get("sub")
    if not usuario:
        raise ApiError("unauthorized", 401, "token sem identificacao de usuario")
    return usuario
