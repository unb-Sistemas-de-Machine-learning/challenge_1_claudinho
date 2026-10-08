"""Cliente unico de LLM, independente de provedor.

Ollama, Gemini, OpenAI, Groq e OpenRouter expoem a mesma API de chat no formato da
OpenAI (`POST <base_url>/chat/completions`). Por isso existe um cliente so, e trocar de
provedor e mudar o `.env`, nao o codigo.

Os provedores sao tentados em ordem: o modelo proprio (Ollama) primeiro, e os externos
so entram quando ele falha ou estoura o tempo. A ordem e montada em
`provedores_configurados`.

Dado de saude (Docs/Ethics e LGPD, Art. 5o, II) nunca vai para provedor externo: o plano
gratuito do Gemini, por exemplo, pode usar o que recebe para treinar. Quem chama marca
`dados_sensiveis=True` e os provedores sem `aceita_dados_sensiveis` sao pulados.
"""

import json
import logging
from dataclasses import dataclass

import httpx

from APP.config import Settings

logger = logging.getLogger("gerador_rag")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
OPENAI_BASE_URL = "https://api.openai.com/v1"

# Os externos respondem em poucos segundos. Esperar mais que isso so atrasa o 503.
TIMEOUT_EXTERNO_S = 25.0


@dataclass(frozen=True)
class Provedor:
    nome: str
    # Ate o /v1, sem o /chat/completions. Ex.: https://usuario-claudinho-llm.hf.space/v1
    base_url: str
    modelo: str
    api_key: str | None = None
    timeout_s: float = TIMEOUT_EXTERNO_S
    # So o modelo hospedado pelo time. Ver o docstring do modulo.
    aceita_dados_sensiveis: bool = False

    @property
    def versao(self) -> str:
        """O que vai para o `model_version` da resposta e do log."""
        return f"{self.nome}/{self.modelo}"


class GeracaoIndisponivel(Exception):
    """Nenhum provedor elegivel conseguiu gerar a resposta."""


def provedores_configurados(settings: Settings) -> list[Provedor]:
    """Monta a cadeia de provedores a partir do ambiente, na ordem de preferencia."""
    provedores = []
    if settings.llm_base_url:
        provedores.append(
            Provedor(
                nome="ollama",
                base_url=settings.llm_base_url,
                modelo=settings.llm_modelo,
                # Token do Hugging Face quando o Space e privado: o proxy do HF aceita o
                # mesmo `Authorization: Bearer` que a API da OpenAI usa.
                api_key=settings.llm_api_key,
                timeout_s=settings.llm_timeout_s,
                aceita_dados_sensiveis=True,
            )
        )
    if settings.gemini_api_key:
        provedores.append(
            Provedor(
                nome="gemini",
                base_url=GEMINI_BASE_URL,
                modelo=settings.gemini_modelo,
                api_key=settings.gemini_api_key,
            )
        )
    if settings.openai_api_key:
        provedores.append(
            Provedor(
                nome="openai",
                base_url=OPENAI_BASE_URL,
                modelo=settings.openai_modelo,
                api_key=settings.openai_api_key,
            )
        )
    return provedores


def gerar_json(
    sistema: str,
    usuario: str,
    provedores: list[Provedor],
    *,
    dados_sensiveis: bool = False,
    transporte: httpx.BaseTransport | None = None,
) -> tuple[dict[str, object], Provedor]:
    """Pede uma resposta em JSON ao primeiro provedor que conseguir gerar.

    Devolve o objeto decodificado e o provedor que respondeu. `transporte` existe para
    os testes trocarem a rede por respostas fixas.
    """
    elegiveis = [p for p in provedores if p.aceita_dados_sensiveis or not dados_sensiveis]
    if not elegiveis:
        raise GeracaoIndisponivel("nenhum provedor elegivel configurado")

    for provedor in elegiveis:
        try:
            return _chamar(provedor, sistema, usuario, transporte), provedor
        except (httpx.HTTPError, ValueError, KeyError, IndexError, AttributeError) as erro:
            # ValueError cobre o JSON quebrado: modelo pequeno as vezes escapa do formato.
            logger.warning("Provedor %s falhou: %s: %s", provedor.versao, type(erro).__name__, erro)

    raise GeracaoIndisponivel("todos os provedores falharam")


def _chamar(
    provedor: Provedor,
    sistema: str,
    usuario: str,
    transporte: httpx.BaseTransport | None,
) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {provedor.api_key}"} if provedor.api_key else {}
    payload = {
        "model": provedor.modelo,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    with httpx.Client(timeout=provedor.timeout_s, transport=transporte) as client:
        resposta = client.post(
            f"{provedor.base_url.rstrip('/')}/chat/completions", headers=headers, json=payload
        )
        resposta.raise_for_status()
        texto = resposta.json()["choices"][0]["message"]["content"]

    # Gemini e OpenAI respondem 200 com content nulo quando o filtro de seguranca recusa,
    # ou quando a resposta so traz tool_calls. Sem esta checagem, _sem_cercas_de_codigo(None)
    # levanta AttributeError, que escapa dos handlers e vira 500: o proximo provedor nao e
    # tentado e o fallback local nao roda.
    if not isinstance(texto, str):
        raise GeracaoIndisponivel("provedor devolveu resposta sem conteudo de texto")

    objeto = json.loads(_sem_cercas_de_codigo(texto))
    if not isinstance(objeto, dict):
        raise ValueError("a resposta do modelo nao e um objeto JSON")
    return objeto


def _sem_cercas_de_codigo(texto: str) -> str:
    """Tira o ```json ... ``` que alguns modelos poem mesmo com o modo JSON ligado."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[1] if "\n" in texto else ""
        texto = texto.removesuffix("```")
    return texto.strip()
