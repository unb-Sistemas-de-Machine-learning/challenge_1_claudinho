# Spec: Observabilidade, feedback e avaliação (MLOps)

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema

Um sistema de RAG responde com confiança mesmo quando piora. Sem registro por requisição, sem opinião de quem usa e sem uma medição repetível, ninguém sabe se uma troca de prompt ou de modelo melhorou ou estragou a resposta. Em saúde isso é mais grave, e o registro não pode virar um vazamento de dado sensível.

## Objetivo

Dar ao time a capacidade de responder, para qualquer resposta dada: qual execução foi essa, com quais versões, o que o usuário achou e como a qualidade evolui entre versões. Tudo isso sem guardar o texto do usuário nem a condição clínica.

## Escopo

### Dentro

- Log estruturado JSON, um registro por requisição, costurado por `trace_id`.
- Registro de versões (`model_version`, `prompt_version`) e de sinais de qualidade (`safe_refusal`, `low_coverage`, `evidencia_suficiente`).
- Endpoint de feedback ligado ao `trace_id`, com motivo, e a UI de avaliação no resultado.
- Avaliação offline com métricas (F2, recall, recusa segura, latência) e código de saída usável como quality gate.
- Comparação de versões de prompt e testes de estresse e cold start.
- Atualização periódica da base científica por agenda (scraper mensal).

### Fora (e por quê)

- Sentry, Langfuse, painel e alertas: previstos em `Docs/Production/02_monitoramento_e_mlops.md`, não existem no código. Pós-MVP: exigem conta, custo e alguém para operar.
- RAGAS no CI: o gate está como TODO em `.github/workflows/ci.yml`. Depende de um benchmark maior (a meta era 50 perguntas, há 10).
- Tags semânticas de versão e prompts em arquivos separados: os prompts são constantes em `APP/model/prompts.py`, com um seletor `VERSAO_ATIVA`. Versionados pelo Git, sem release tag.
- Detecção automática de drift (cobertura média de 7 dias, agrupamento de lacunas): só o sinal bruto `low_coverage` é registrado.
- Triagem semanal automatizada do feedback: hoje a leitura é manual na tabela.

## Requisitos funcionais

- RF-01: toda requisição fora de `/health`, `/docs`, `/redoc`, `/openapi.json` e `/favicon.ico` emite exatamente um registro JSON em stdout, com `trace_id`, `timestamp`, `endpoint`, `status` e `performance.total_latency_ms`.
- RF-02: o `trace_id` do log é o mesmo devolvido na resposta da checagem e aceito pelo feedback.
- RF-03: o usuário aparece no log só como hash (`sha256:...`) da identidade resolvida (claim `sub`), igual ao usado pelo rate limit.
- RF-04: o log da checagem registra `model_version` e `prompt_version`.
- RF-05: o log registra `low_coverage` (recuperação), `evidencia_suficiente` (geração) e `safe_refusal` (guardrails).
- RF-06: o log registra se o perfil foi usado e se há condições, só como booleanos (`profile.usado`, `profile.has_conditions`).
- RF-07: o texto digitado e o comentário livre do feedback nunca entram no log (só tamanho e `tem_comentario`).
- RF-08: `POST /api/v1/feedback` exige autenticação, aplica limite de escrita e responde 201 com `feedback_id`.
- RF-09: o feedback aceita `rating` (`up` ou `down`), `reason` opcional (`fonte_irrelevante`, `resposta_confusa`, `parece_errado`, `tom_julgador`, `nao_respondeu`, `outro`) e `comment` de até 2000 caracteres.
- RF-10: um `trace_id` que não é UUID é recusado na entrada.
- RF-11: o feedback é gravado na tabela `feedback` do Supabase quando configurado, ou em memória caso contrário.
- RF-12: a tela de resultado oferece "Ajudou" e "Não ajudou", e esta última pede o motivo.
- RF-13: `benchmarks/avaliar_pipeline.py` calcula F2, recall, taxa de recusa segura e latência, e sai com 0 (metas atingidas), 1 (meta reprovada) ou 2 (requisições sem resposta).
- RF-14: `benchmarks/comparar_prompts.py` roda o mesmo conjunto com versões diferentes de prompt e gera `comparacao_prompts.md`.
- RF-15: o scraper do PubMed roda no dia 1 de cada mês e também sob demanda (`.github/workflows/article_scraper.yml`).

## Requisitos não funcionais

- Privacidade: dado de saúde e identidade fora do log (LGPD). O hash usa a identidade, não o token, para ser estável quando o access token é rotacionado.
- Falha segura: erro ao buscar o perfil não derruba a checagem e fica registrado só pelo tipo do erro.
- Esquema estável: os blocos `nlp`, `retrieval`, `generation` e `guardrails` existem sempre, com `None` quando a etapa não rodou.
- Idempotência: `configurar_logging` não duplica o handler.
- Custo zero de infraestrutura nova: o log sai em stdout, coletado pelo provedor.

## Critérios de aceite

- [x] Um registro por requisição, sem copiar o texto do usuário (`tests/test_logging_estruturado.py`, incluindo `test_o_texto_do_usuario_nao_vai_para_o_log`).
- [x] Hash do usuário no log (`tests/test_logging_estruturado.py`).
- [x] Falha ao buscar o perfil não derruba a checagem e é logada (`tests/test_perfil_na_checagem.py`).
- [x] Sinais da recuperação no log (`tests/test_retriever_observabilidade.py`).
- [x] Feedback registrado, com autenticação exigida (`tests/test_feedback.py`).
- [x] Repositório de feedback em memória e Supabase (`tests/test_repositorio_feedback.py`).
- [x] Métricas e código de saída do benchmark (`tests/test_benchmarks.py`).
- [x] Comparação de prompts (`tests/test_comparar_prompts.py`).
- [x] UI de avaliação com motivos (`web/src/componentes/Avaliacao.tsx`).
- [ ] Benchmark com 50 perguntas (hoje `benchmarks/dataset_benchmark.json` tem 10 casos).
- [ ] Prompt `rag-v2.2`, o ativo, comparado com as versões anteriores (`comparacao_prompts.md` cobre só v1.0 e v2.0).
- [ ] Quality gate (benchmark ou RAGAS) rodando no CI (o CI roda só `pytest` e o build).
- [ ] Painel e alertas (Langfuse ou Grafana) e Sentry.
- [ ] Teste automatizado do próprio workflow do scraper e da frescura da base.

## Decisões

| Decisão | Por quê | Onde |
|---|---|---|
| Um registro JSON por requisição | Evita join de eventos parciais na análise | `APP/middleware.py`, `APP/observabilidade.py` |
| Contexto em dicionário mutável num `ContextVar` | O middleware do Starlette roda a rota em outra task; só um objeto compartilhado enxerga as mudanças | `APP/observabilidade.py` |
| Hash da identidade, não do token | O token rotaciona de hora em hora e quebraria o agrupamento | `hash_de_usuario` em `APP/observabilidade.py` |
| Log só com booleanos sobre o perfil | Condição clínica é dado sensível | `APP/routers/check_claim.py` |
| `comment` livre fora do log | O usuário pode escrever condição clínica ali | `APP/routers/feedback.py` |
| `reason` opcional no feedback | Exigir motivo derrubaria o volume de avaliações | `APP/schemas.py` |
| Repositório com Protocol (memória ou Supabase) | Testes sem rede e deploy sem banco continuam funcionando | `APP/repositorios/feedback.py` |
| Prompts como constantes versionadas (`rag-v1.0` a `rag-v2.2`) | Simples, versionado no Git, troca por uma variável | `APP/model/prompts.py` |
| Benchmark com código de saída | Permite virar gate de CI sem ferramenta nova | `benchmarks/avaliar_pipeline.py` |
| Scraper por agenda mensal como gatilho de atualização | Em RAG, "retreino" é atualizar a base | `.github/workflows/article_scraper.yml` |

## Riscos e limitações conhecidas

- Dez casos de benchmark não sustentam conclusão estatística. Servem de fumaça, não de prova.
- A versão de prompt ativa (v2.2) nunca foi comparada. A qualidade atual não tem linha de base registrada.
- Sem painel nem alerta, um problema só é visto se alguém ler o log ou a tabela de feedback.
- O limiar de `low_coverage` depende do modelo de embedding e precisa ser remedido se ele mudar (ver `Docs/Production/02_monitoramento_e_mlops.md`).
- Feedback em memória (sem Supabase) some ao reiniciar a função.
- A doc de produção promete mais do que o código entrega. Esta spec é a fonte do que realmente existe.

## Referências

- `Docs/Production/02_monitoramento_e_mlops.md` e `Docs/Production/01`.
- Issue #36 (log estruturado e feedback), #9 (benchmark), #33 (tela de resultado e avaliação), #50 (scraper).
- PR #2 (log e feedback), #15 (observabilidade, benchmark e prompt v2), #53 (scraper), #61 (veredito `sem_evidencia`).
- Kreuzberger, Kühl e Hirschl. Machine Learning Operations (MLOps): Overview, Definition, and Architecture. IEEE Access, 2023.

### Os 9 princípios do artigo e o Claudinho

| Princípio | O que o Claudinho tem |
|---|---|
| CI/CD | CI com pytest, build e front; falta o gate de qualidade |
| Orquestração | GitHub Actions (CI e scraper); sem orquestrador de pipeline |
| Reprodutibilidade | Dataset e scripts em `benchmarks/`, dependências travadas; LLM externa varia |
| Versionamento | Git, `prompt_version` e `model_version` no log; sem tags semânticas |
| Colaboração | PRs com revisão, issues por frente, branches protegidas |
| Treino contínuo | Em RAG, atualizar a base: scraper mensal (gatilho por agenda) |
| Metadados | `trace_id`, versões, sinais de cobertura e evidência por requisição |
| Monitoramento | Log estruturado em stdout; sem painel nem alerta |
| Feedback | `POST /feedback` ligado ao `trace_id` e UI com motivos |
