"""Gerador grounded com ancoragem estrita (Strict Grounding).

O LLM e chamado por APP/model/llm.py, que tenta o modelo proprio (Ollama) antes dos
provedores externos.

Documentado em:
- Docs/Model/02_arquitetura_nlp_rag.md (Strict Grounding e System Prompt)
- Docs/User/01_personas.md (Tom de voz e persona Lucas)
- Docs/Model/01_metricas_e_avaliacao.md (Limiares de decisao e calibracao)
"""

import logging
import re
from typing import Literal

from APP.config import Settings
from APP.model import prompts
from APP.model.classifier import (
    calcular_risco_evidencia,
    classificar_padrao_semantico,
)
from APP.model.llm import GeracaoIndisponivel, gerar_json, provedores_configurados
from APP.model.resposta_local import MODEL_VERSION as MODEL_VERSION_LOCAL
from APP.model.resposta_local import montar_resposta_local
from APP.model.retriever import formatar_contexto_cientifico
from APP.observabilidade import adicionar_ao_log
from APP.schemas import Fonte
from APP.verdict import LIMIAR_DESINFORMACAO, LIMIAR_SEGURO, classificar_veredito

logger = logging.getLogger("gerador_rag")


# Sem estudos na base nao ha o que citar, entao nao ha LLM: o texto e fixo. Segue as
# mesmas regras do prompt v2 (Docs/User/01, secao 2.2): resposta primeiro, conversa,
# franqueza sobre o limite da base, e nenhum sermao.
RESPOSTA_SEM_EVIDENCIA = (
    "Ainda não temos estudos sobre isso, então não dá para confirmar nem descartar. "
    "Enquanto isso, desconfie de posts que prometem resultado rápido ou que culpam um "
    "alimento sozinho, porque é assim que a maioria dos mitos circula. Se a dúvida tem a ver "
    "com a sua saúde, um nutricionista ou médico pode olhar o seu caso."
)


def _definir_nivel_risco(score: float) -> Literal["baixo", "medio", "alto"]:
    """Nivel de risco a partir dos MESMOS limiares do veredito (APP/verdict.py).

    Repetir 0.35 e 0.65 aqui fazia a calibracao ter dois donos: mudar o limiar no
    verdict.py, que a documentacao aponta como a regra, deixava a resposta incoerente
    consigo mesma (verdict "cautela" com risk_level "alto").
    """
    if score < LIMIAR_SEGURO:
        return "baixo"
    if score <= LIMIAR_DESINFORMACAO:
        return "medio"
    return "alto"


def gerar_resposta_grounded(
    alegacao_canonica: str,
    fontes: list[Fonte],
    raw_chunks: list[dict[str, object]],
    settings: Settings,
    pergunta_amigavel: str = "",
    dados_sensiveis: bool = False,
) -> tuple[str, float, str, str, str]:
    """Gera a resposta ancorada nos chunks científicos em tom humano e acolhedor.

    `dados_sensiveis` deve ser True quando o perfil de saude entrar no prompt: assim a
    geracao fica restrita ao modelo proprio (ver APP/model/llm.py).

    Retorna tupla:
      (answer, risk_score, verdict, model_version, prompt_version)
    """
    prompt_version, prompt_sistema, tag_estudos = prompts.ativo()
    pergunta_exibicao = pergunta_amigavel or alegacao_canonica

    # Caso 1: Nenhuma fonte recuperada na base
    if not fontes or not raw_chunks:
        answer = RESPOSTA_SEM_EVIDENCIA
        score = 0.50
        return (
            answer,
            score,
            "sem_evidencia",
            "retriever@multilingual-e5-base",
            prompt_version,
        )

    contexto_str = formatar_contexto_cientifico(raw_chunks)
    provedores = provedores_configurados(settings)

    prompt_usuario = (
        f"<{tag_estudos}>\n{contexto_str}\n</{tag_estudos}>\n\n"
        f"Pergunta do usuário: {pergunta_exibicao}"
    )
    try:
        resposta_llm, provedor = gerar_json(
            prompt_sistema,
            prompt_usuario,
            provedores,
            dados_sensiveis=dados_sensiveis,
        )
        # Fora do try, uma resposta sem "answer" viraria a string "None" na tela do app.
        answer = _validar_resposta(resposta_llm["answer"], raw_chunks)
        score = max(0.0, min(1.0, float(resposta_llm.get("risk_score", 0.5))))
    except (GeracaoIndisponivel, KeyError, TypeError, ValueError, AttributeError) as erro:
        # Nenhum provedor respondeu (Space dormindo, cota esgotada, timeout). Em vez de
        # devolver 503, o classificador de regras decide o veredito e a resposta e
        # montada a partir dos proprios trechos recuperados. E local: nao envia nada
        # para fora, entao vale tambem quando `dados_sensiveis` e True.
        logger.warning("Geracao indisponivel, usando fallback local: %s", erro)
        return _responder_localmente(alegacao_canonica, fontes, raw_chunks, pergunta_exibicao)

    padrao = classificar_padrao_semantico(alegacao_canonica) or classificar_padrao_semantico(
        pergunta_exibicao
    )
    if padrao is not None:
        score_padrao, categoria = padrao
        if categoria == "desinformacao":
            score = max(score, score_padrao)
        elif categoria == "seguro":
            score = min(score, score_padrao)
        elif score < LIMIAR_SEGURO or score > LIMIAR_DESINFORMACAO:
            score = score_padrao

    return answer, score, classificar_veredito(score), provedor.versao, prompt_version


_REFERENCIA = re.compile(r"\[Ref:\s*([^\]]+)\]")
# O modelo as vezes repete o rotulo dentro da citacao ("[Ref: Ref: abc]" ou
# "[Ref: ID_CHUNK: abc]"). O ID e real; so a formatacao veio torta. Sem tirar o rotulo,
# a resposta era rejeitada como se citasse um estudo inventado.
_ROTULO = re.compile(r"^(?:\s*(?:ref|id_chunk|id)\s*:\s*)+", re.IGNORECASE)


def ids_citados(texto: str) -> set[str]:
    """IDs citados em [Ref: ...], sem rotulos repetidos. Aceita varios IDs separados por virgula."""
    ids = (
        _ROTULO.sub("", parte).strip()
        for grupo in _REFERENCIA.findall(texto)
        for parte in grupo.split(",")
    )
    return {i for i in ids if i}


def _validar_resposta(answer: object, raw_chunks: list[dict[str, object]]) -> str:
    """Confere a resposta da LLM antes de ela chegar ao usuario.

    Levanta ValueError, que o gerador trata como falha e responde pelo fallback local
    (ancorado so em trechos reais), quando:
    - a resposta vem vazia ou nao e texto: chegaria em branco ao app;
    - cita um estudo que o retriever nao devolveu: o modelo inventou a fonte, e a
      afirmacao ligada a ela provavelmente tambem (Docs/Ethics/01, anti-alucinacao).
    """
    if not isinstance(answer, str) or not answer.strip():
        adicionar_ao_log(generation={"rejeitada": "resposta_vazia"})
        raise ValueError("resposta vazia da LLM")

    recuperados = {str(c.get("chunk_id", "")) for c in raw_chunks}
    citados = ids_citados(answer)
    inventados = citados - recuperados
    if inventados:
        adicionar_ao_log(
            generation={"rejeitada": "referencia_inexistente", "refs_invalidas": len(inventados)}
        )
        raise ValueError(f"LLM citou estudo nao recuperado: {sorted(inventados)}")

    return answer.strip()


def _responder_localmente(
    alegacao: str,
    fontes: list[Fonte],
    raw_chunks: list[dict[str, object]],
    pergunta: str,
) -> tuple[str, float, str, str, str]:
    score, _ = calcular_risco_evidencia(alegacao, fontes, raw_chunks)
    # O veredito sai dos mesmos limiares 0.35 / 0.65 do resto da API (APP/verdict.py),
    # e nao da string devolvida pelo classificador, para haver uma unica fonte da regra.
    veredito = classificar_veredito(score)
    trechos = {str(c.get("chunk_id", "")): str(c.get("conteudo") or "") for c in raw_chunks}
    resposta = montar_resposta_local(veredito, pergunta, fontes, trechos)
    return resposta, score, veredito, MODEL_VERSION_LOCAL, "fallback-template-v1"
