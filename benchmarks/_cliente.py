"""Cliente HTTP comum ao benchmark e ao teste de estresse.

Dois modos:
- **em processo** (padrao): chama a aplicacao direto, sem subir servidor. Usa a
  configuracao do .env, entao roda com a LLM real se a chave estiver configurada.
- **remoto** (`--url`): mede uma API de verdade, local ou publicada.
"""

import httpx

TIMEOUT_S = 60.0


def criar_cliente(url: str | None) -> httpx.AsyncClient:
    if url:
        return httpx.AsyncClient(base_url=url.rstrip("/"), timeout=TIMEOUT_S)

    from APP.main import app  # importado so aqui: o modo remoto nao precisa da app

    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://benchmark", timeout=TIMEOUT_S
    )


def cabecalho(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
