"""Pipeline central de checagem conectando NLP, Recuperacao, Geracao e Guardrails.

Documentado em Docs/Production/01_plataforma_e_deploy.md, secao 1.1.
"""

from APP.config import Settings
from APP.errors import ApiError
from APP.model import disclaimers
from APP.model.claim_extractor import (
    checar_recusa_segura,
    normalizar_alegacao_heuristica,
    reformular_pergunta_amigavel,
)
from APP.model.classifier import classificar_padrao_semantico
from APP.model.generator import (
    _definir_nivel_risco,
    gerar_resposta_grounded,
)
from APP.model.retriever import (
    RecuperacaoIndisponivel,
    buscar_evidencias_cientificas,
    detectar_e_comparar_tbca,
)
from APP.observabilidade import adicionar_ao_log
from APP.schemas import CheckClaimRequest, CheckClaimResponse


def executar_pipeline_de_checagem(
    requisicao: CheckClaimRequest,
    settings: Settings,
    latency_ms: int,
    trace_id: str,
) -> CheckClaimResponse:
    """Executa o fluxo completo do pipeline RAG anti-alucinacao."""
    # OCR de print e leitura de pagina ainda nao existem. Antes, imagem virava a frase fixa
    # "Analise de imagem recebida via upload" e link virava a propria URL: as duas
    # alimentavam embedding, guardrails e prompt, e o usuario recebia um veredito confiante,
    # com fontes e DOI, sobre um assunto que nao tinha relacao com o que ele mandou.
    # Recusar e melhor do que responder errado com cara de certo.
    if not requisicao.text:
        raise ApiError(
            "input_nao_suportado",
            422,
            "Ainda não conseguimos ler prints nem links. Escreva a dúvida em texto que a "
            "gente verifica para você.",
        )

    texto_entrada = requisicao.text
    pergunta_amigavel = reformular_pergunta_amigavel(texto_entrada)

    # 0. Menor de 18 anos: recusa de servico (Docs/Ethics/02, LGPD Art. 14). Vem antes de
    # tudo: nao ha checagem a oferecer, nem mesmo a resposta de cuidado dos guardrails.
    if disclaimers.e_menor_de_idade(texto_entrada):
        adicionar_ao_log(guardrails={"restricao_de_idade": True})
        return CheckClaimResponse(
            trace_id=trace_id,
            canonical_claim=pergunta_amigavel,
            verdict="recusa_segura",
            risk_score=1.0,
            risk_level="alto",
            answer=disclaimers.MENOR_DE_IDADE,
            sources=[],
            disclaimer=disclaimers.CURTO,
            cached=False,
            latency_ms=latency_ms,
            model_version="guardrail@ethics-v1",
            prompt_version="restricao-de-idade-v1",
        )

    # 1. Checagem previa de Guardrails de Seguranca (Ethics/01 e Ethics/02)
    acionou_recusa, mensagem_recusa = checar_recusa_segura(texto_entrada, pergunta_amigavel)
    adicionar_ao_log(guardrails={"safe_refusal": acionou_recusa})
    if acionou_recusa:
        return CheckClaimResponse(
            trace_id=trace_id,
            canonical_claim=pergunta_amigavel,
            verdict="recusa_segura",
            risk_score=1.0,
            risk_level="alto",
            answer=mensagem_recusa,
            sources=[],
            disclaimer=disclaimers.montar_disclaimer("recusa_segura", texto_entrada),
            cached=False,
            latency_ms=latency_ms,
            model_version="guardrail@ethics-v1",
            prompt_version="safe-refusal-v1",
        )

    # 2. Extracao de alegacao canonica para busca cientifica (Model/03)
    alegacao_canonica = normalizar_alegacao_heuristica(texto_entrada)

    # 2.1. Sinal semantico previo para observabilidade (Docs/Model/03 e Model/04)
    padrao_semantico = classificar_padrao_semantico(texto_entrada) or classificar_padrao_semantico(
        alegacao_canonica
    )
    if padrao_semantico:
        adicionar_ao_log(
            classifier={"padrao": padrao_semantico[1], "score_prior": padrao_semantico[0]}
        )

    # 3. Checagem de dados e comparacao na tabela alimentar TBCA do Supabase
    dados_tbca, fontes_tbca = detectar_e_comparar_tbca(texto_entrada)
    if dados_tbca and fontes_tbca:
        raw_chunks_tbca = [
            {
                "chunk_id": f.chunk_id,
                "titulo": f.title,
                "conteudo": f.excerpt,
            }
            for f in fontes_tbca
        ]
        answer, risk_score, verdict, model_ver, prompt_ver = gerar_resposta_grounded(
            alegacao_canonica=alegacao_canonica,
            fontes=fontes_tbca,
            raw_chunks=raw_chunks_tbca,
            settings=settings,
            pergunta_amigavel=pergunta_amigavel,
        )
        return CheckClaimResponse(
            trace_id=trace_id,
            canonical_claim=pergunta_amigavel,
            verdict=verdict,
            risk_score=risk_score,
            risk_level=_definir_nivel_risco(risk_score),
            answer=answer,
            sources=fontes_tbca,
            disclaimer=disclaimers.montar_disclaimer(verdict, texto_entrada),
            cached=False,
            latency_ms=latency_ms,
            model_version=model_ver,
            prompt_version=prompt_ver,
        )

    # 4. Recuperacao semantica no pgvector do Supabase (Data/02 e Model/02)
    try:
        fontes, raw_chunks = buscar_evidencias_cientificas(alegacao_canonica)
    except RecuperacaoIndisponivel as erro:
        # Contrato da API (Docs/Production/01, secao 2.1): 503 upstream_unavailable.
        raise ApiError(
            "upstream_unavailable",
            503,
            "A busca de estudos está indisponível no momento. Tente de novo em instantes.",
        ) from erro

    # 4. Geracao grounded ancorada estritamente nas evidencias (Model/02)
    answer, risk_score, verdict, model_ver, prompt_ver = gerar_resposta_grounded(
        alegacao_canonica=alegacao_canonica,
        fontes=fontes,
        raw_chunks=raw_chunks,
        settings=settings,
        pergunta_amigavel=pergunta_amigavel,
    )

    return CheckClaimResponse(
        trace_id=trace_id,
        canonical_claim=pergunta_amigavel,
        verdict=verdict,
        risk_score=risk_score,
        risk_level=_definir_nivel_risco(risk_score),
        answer=answer,
        sources=fontes,
        disclaimer=disclaimers.montar_disclaimer(verdict, texto_entrada),
        cached=False,
        latency_ms=latency_ms,
        model_version=model_ver,
        prompt_version=prompt_ver,
    )
