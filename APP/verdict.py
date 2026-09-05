"""Traducao do risk_score para o veredito exposto pela API.

Os limiares (0.35 e 0.65) sao definidos pela frente de Modelo em
Docs/Model/01_metricas_e_avaliacao.md e replicados em
Docs/Production/01_plataforma_e_deploy.md, secao 2.1.
"""

LIMIAR_SEGURO = 0.35
LIMIAR_DESINFORMACAO = 0.65


def classificar_veredito(risk_score: float) -> str:
    """Devolve `seguro`, `cautela` ou `desinformacao` a partir do score.

    Os vereditos `sem_evidencia` e `recusa_segura` nao dependem do score:
    o primeiro vem da recuperacao sem cobertura e o segundo dos guardrails.
    """
    if not 0.0 <= risk_score <= 1.0:
        raise ValueError(f"risk_score deve estar entre 0.0 e 1.0, recebido: {risk_score}")

    if risk_score < LIMIAR_SEGURO:
        return "seguro"
    if risk_score <= LIMIAR_DESINFORMACAO:
        return "cautela"
    return "desinformacao"
