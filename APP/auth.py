"""Autenticacao da API: validacao do JWT emitido pelo Supabase Auth.

O Supabase assina tokens de dois jeitos, e a API aceita os dois:

- **Chaves assimetricas (ES256/RS256)**: padrao em todo projeto criado desde outubro de
  2025. A API valida com as chaves PUBLICAS do projeto, publicadas em
  `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. Nao ha segredo para configurar.
- **Segredo compartilhado (HS256)**: formato antigo. Exige `SUPABASE_JWT_SECRET`.

Em qualquer um, a assinatura, a expiracao e a audiencia sao conferidas, e a identidade
devolvida e o `sub` (id do usuario no Supabase).

**Modo local**: com `APP_ENV=local` e sem `SUPABASE_JWT_SECRET`, qualquer token nao vazio e
aceito e devolvido como identidade. Serve para desenvolvimento e para a suite de testes.
Ele depende EXPLICITAMENTE de `APP_ENV=local`: fora disso, todo token e validado. Antes, o
modo local era "segredo vazio", o que deixaria a autenticacao desligada num deploy com a
variavel esquecida; com as chaves assimetricas, segredo vazio passou a ser o normal.

A identidade precisa ser ESTAVEL entre sessoes: e ela que indexa o perfil de saude e o
balde do rate limit. Usar o token cru daria um id novo a cada renovacao (o Supabase
rotaciona o access token de hora em hora), o perfil sumiria depois de sair e entrar de
novo e a cota se renovaria sozinha a cada refresh.
"""

import logging
from functools import lru_cache

import jwt
from fastapi import Depends, Request
from starlette.concurrency import run_in_threadpool

from APP.config import Settings, obter_settings
from APP.errors import ApiError

# Formato antigo, com segredo compartilhado.
ALGORITMO = "HS256"
# Formato atual, com chave publica. Cada algoritmo so e aceito com a chave do seu tipo:
# aceitar HS256 usando a chave publica como "segredo" permitiria forjar tokens.
ALGORITMOS_ASSIMETRICOS = ("ES256", "RS256")
AUDIENCIA = "authenticated"


def verificar_configuracao(settings: Settings) -> None:
    """Falha rapido na subida quando o ambiente nao esta pronto para valer.

    Sem as origens, o navegador bloqueia toda chamada do app antes de ela sair da
    maquina, sem erro no servidor e sem linha de log.
    """
    if settings.app_env == "local":
        return

    # SUPABASE_JWT_SECRET deixou de ser obrigatorio: projetos atuais validam pelas chaves
    # publicas do SUPABASE_URL, e fora do modo local nenhum token passa sem validacao.
    faltando = []
    if not settings.origens_permitidas:
        faltando.append("ORIGENS_PERMITIDAS (sem ela o navegador bloqueia as chamadas do app)")

    if faltando:
        raise RuntimeError(
            f"Configuracao obrigatoria ausente com APP_ENV={settings.app_env!r}: "
            + "; ".join(faltando)
        )


def token_do_header(authorization: str | None) -> str | None:
    """Extrai o token do header `Authorization: Bearer <token>`."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip() or None


def identidade_do_token(token: str, settings: Settings) -> str:
    """Devolve a identidade do usuario ou levanta `unauthorized`."""
    if settings.app_env == "local" and not settings.supabase_jwt_secret:
        return token  # modo local

    try:
        algoritmo = jwt.get_unverified_header(token).get("alg")
        if algoritmo in ALGORITMOS_ASSIMETRICOS:
            chave = _chaves_publicas(settings.supabase_url).get_signing_key_from_jwt(token).key
        elif algoritmo == ALGORITMO and settings.supabase_jwt_secret:
            chave = settings.supabase_jwt_secret
        else:
            raise jwt.InvalidAlgorithmError(f"algoritmo nao aceito: {algoritmo}")

        payload = jwt.decode(token, chave, algorithms=[algoritmo], audience=AUDIENCIA)
    except jwt.ExpiredSignatureError:
        raise ApiError("unauthorized", 401, "token expirado") from None
    except jwt.PyJWKClientConnectionError:
        # Nao conseguiu buscar as chaves publicas: e falha de infraestrutura, nao do usuario.
        raise ApiError(
            "upstream_unavailable", 503, "Validacao de login indisponivel. Tente de novo."
        ) from None
    except (jwt.InvalidTokenError, jwt.PyJWKClientError):
        # Assinatura invalida, audiencia errada, chave desconhecida, formato quebrado: a
        # causa exata nao volta para o cliente, ela so ajudaria quem tenta forjar um token.
        raise ApiError("unauthorized", 401, "token invalido") from None

    usuario = payload.get("sub")
    if not usuario:
        raise ApiError("unauthorized", 401, "token sem identificacao de usuario")
    return usuario


@lru_cache(maxsize=4)
def _chaves_publicas(supabase_url: str) -> jwt.PyJWKClient:
    """Cliente das chaves publicas do projeto, com cache.

    Uma instancia por processo: o PyJWKClient guarda as chaves e so busca de novo quando
    aparece um `kid` desconhecido (rotacao de chave) ou o cache expira.
    """
    return jwt.PyJWKClient(
        f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        lifespan=3600,
        timeout=5,
    )


_SEM_IDENTIDADE = object()


async def resolver_identidade(request, settings: Settings | None = None):
    """Valida o token UMA vez por requisicao e guarda o resultado em `request.state`.

    Duas razoes:

    - **Custo.** A mesma validacao era feita tres vezes (middleware de log, rate limit e
      dependencia da rota). Com HS256 era barato; com chave assimetrica, nao e.
    - **Bloqueio do event loop.** Buscar a chave publica e HTTP bloqueante. Quando o `kid`
      nao esta em cache, o PyJWT vai a rede. Chamado direto de um caminho async, isso
      congela a API inteira, inclusive o /health: bastaria repetir tokens com `kid`
      aleatorio para derrubar tudo. Aqui a validacao roda na threadpool.

    Devolve a identidade, ou None quando nao ha token valido. Guarda tambem o erro, para
    a dependencia da rota poder levanta-lo sem revalidar.
    """
    if hasattr(request.state, "identidade"):
        return request.state.identidade

    token = token_do_header(request.headers.get("authorization"))
    request.state.erro_de_autenticacao = None
    if token is None:
        request.state.identidade = None
        request.state.erro_de_autenticacao = ApiError("unauthorized", 401)
        return None

    try:
        identidade = await run_in_threadpool(
            identidade_do_token, token, settings or obter_settings()
        )
    except ApiError as erro:
        request.state.identidade = None
        request.state.erro_de_autenticacao = erro
        return None

    request.state.identidade = identidade
    return identidade


def preparar_chaves_publicas(settings: Settings) -> None:
    """Baixa as chaves publicas na subida, para a primeira requisicao nao pagar a rede.

    Falha aqui nao derruba a aplicacao: o Supabase pode estar fora do ar no deploy, e a
    busca acontece de novo sob demanda.
    """
    if settings.app_env == "local" and not settings.supabase_jwt_secret:
        return
    try:
        _chaves_publicas(settings.supabase_url).get_signing_keys()
    except Exception as erro:  # noqa: BLE001 - qualquer falha aqui e tolerada
        logging.getLogger("claudinho").warning(
            "Nao foi possivel pre-carregar as chaves publicas: %s", type(erro).__name__
        )


def identidade_do_header(authorization: str | None, settings: Settings | None = None) -> str | None:
    """Mesma identidade da rota, porem sem levantar erro.

    Serve para quem roda ANTES da rota e nao pode interromper a requisicao: o middleware
    de log e a checagem de rate limit. Token ausente ou invalido devolve None, e quem
    chamou decide o que fazer (o log grava `user_id_hash: null`, o rate limit cai no IP).
    """
    token = token_do_header(authorization)
    if token is None:
        return None
    try:
        return identidade_do_token(token, settings or obter_settings())
    except ApiError:
        return None


async def exigir_autenticacao(
    request: Request,
    settings: Settings = Depends(obter_settings),
) -> str:
    """Dependencia das rotas autenticadas. Devolve a identidade do usuario.

    Reaproveita a validacao ja feita no middleware; nao revalida o token.
    """
    identidade = await resolver_identidade(request, settings)
    if identidade is None:
        raise getattr(request.state, "erro_de_autenticacao", None) or ApiError("unauthorized", 401)
    return identidade
