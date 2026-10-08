# Spec: Checagem com RAG e veredito

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema
Alegações de nutrição circulam na internet sem fonte e com tom de certeza. A pessoa não tem como saber se "água com limão queima gordura" tem respaldo científico. Um LLM sozinho responderia com confiança mesmo sem base, e isso é perigoso em saúde.

## Objetivo
Receber uma dúvida em texto, buscar estudos científicos brasileiros relevantes e devolver um veredito claro, com explicação curta e fontes, sem inventar nada além do que os estudos dizem. Quando não houver base, dizer isso.

## Escopo
### Dentro
- Endpoint `POST /api/v1/check-claim` com entrada em texto.
- Guardrails antes de qualquer busca: menor de 18 anos e condutas de risco (recusa segura).
- Extração e normalização da alegação, com reformulação amigável da pergunta.
- Desvio para a tabela TBCA quando a pergunta é de composição de alimento.
- Busca semântica no pgvector do Supabase e geração ancorada nos trechos recuperados.
- Veredito: `seguro`, `cautela`, `desinformacao`, `sem_evidencia`, `recusa_segura`.
- Validação anti-alucinação das citações e fallback local sem LLM.
- Roteamento de provedores de LLM (modelo próprio e Gemini), com dado sensível só no modelo próprio.

### Fora (e por quê)
- Leitura de print (OCR) e de link: não existem. Imagem ou link sem texto recebe 422 `input_nao_suportado`, porque responder sobre o que não foi lido seria um veredito errado com cara de certo.
- Calibração do `low_coverage`: o limiar 0.75 não foi calibrado, então o sinal só vai para o log.
- Cobertura ampla de composição de alimentos: a base atual tem pouco conteúdo desse tipo.
- Cache de respostas: o campo `cached` existe no contrato e sai sempre `false`.

## Requisitos funcionais
- RF-01: o endpoint recusa com 422 `input_nao_suportado` a requisição sem texto (imagem ou link).
- RF-02: texto de menor de 18 anos devolve `recusa_segura`, sem busca e sem chamar LLM.
- RF-03: condutas de risco (jejum extremo, purgação, anorexígenos, entre outras) devolvem `recusa_segura` com resposta de cuidado.
- RF-04: a alegação é normalizada e a pergunta reformulada de forma amigável (`canonical_claim`).
- RF-05: perguntas sobre composição de alimento consultam a TBCA antes da busca nos estudos.
- RF-06: a busca semântica usa embeddings multilingual-e5 sobre o pgvector do Supabase.
- RF-07: se o Supabase de busca estiver fora, a API responde 503 `upstream_unavailable`.
- RF-08: a resposta é gerada só a partir dos trechos recuperados (geração grounded).
- RF-09: o veredito sai do `risk_score` pelos limiares: abaixo de 0.35 `seguro`, até 0.65 `cautela`, acima `desinformacao`. O texto da LLM não decide o veredito.
- RF-10: com `risk_score` fora de 0 a 1, o valor é limitado à faixa.
- RF-11: o prompt ativo (`rag-v2.2`) pede o campo `evidencia_suficiente`. Se for `false`, o veredito é `sem_evidencia` e `sources` vai vazio.
- RF-12: base sem estudos devolve `sem_evidencia` sem chamar a LLM.
- RF-13: resposta que cita um chunk não recuperado é descartada e a resposta local determinística entra no lugar.
- RF-14: resposta quebrada, vazia ou fora do formato da LLM também cai no fallback local.
- RF-15: com perfil de saúde com condições, só o modelo próprio recebe o prompt. Sem ele, vale o fallback local.
- RF-16: o disclaimer da resposta considera avisos do texto e do perfil (por exemplo gestante).
- RF-17: na rota TBCA o campo `evidencia_suficiente` é ignorado (`aceitar_sem_evidencia=False`).
- RF-18: cada resposta traz `trace_id`, `model_version` e `prompt_version`.

## Requisitos não funcionais
- RNF-01 (segurança): o endpoint exige token e tem rate limit (PR #6 e PR #14).
- RNF-02 (privacidade): dado de saúde nunca vai a provedor externo (LGPD).
- RNF-03 (desempenho): orçamento de tempo da requisição fechado com os timeouts em série (LLM 90 s, embeddings 10 s) e com o teto da função na Vercel de 300 s.
- RNF-04 (disponibilidade): a checagem continua respondendo quando nenhum provedor de LLM está no ar, pelo fallback local.
- RNF-05 (observabilidade): log estruturado por requisição, com guardrails, classificador e `low_coverage`.
- RNF-06 (reprodutibilidade): prompts versionados em um único arquivo e a mesma pergunta recebe a mesma resposta local.
- RNF-07 (linguagem): resposta curta, sem emojis, com o veredito na primeira frase.

## Critérios de aceite
- [x] Imagem e link são recusados com 422 e sem chamar a base: `tests/test_review_correcoes.py`
- [x] Contrato completo da resposta e `trace_id` distinto por requisição: `tests/test_check_claim.py`
- [x] Guardrail responde sem buscar na base e sem chamar a LLM: `tests/test_pipeline.py`
- [x] Condutas de risco barradas e dúvidas legítimas liberadas: `tests/test_guardrails.py`
- [x] Base sem estudos vira `sem_evidencia` sem custo de LLM: `tests/test_pipeline.py`
- [x] Veredito segue os limiares e o score é limitado: `tests/test_pipeline.py`, `tests/test_verdict.py`
- [x] Citação de fonte não recuperada cai no fallback: `tests/test_pipeline.py`
- [x] `evidencia_suficiente` false vira `sem_evidencia` sem fontes: `tests/test_veredito_sem_evidencia.py`
- [x] Comparação TBCA não vira `sem_evidencia`: `tests/test_veredito_sem_evidencia.py`
- [x] Prompt ativo é o `rag-v2.2`: `tests/test_prompts.py`
- [x] Dado sensível não vai a provedor externo e há fallback sem provedor: `tests/test_llm.py`
- [x] Fallback local curto, determinístico e só com chunks reais: `tests/test_resposta_local.py`
- [x] Busca semântica e observabilidade da recuperação: `tests/test_retriever.py`, `tests/test_retriever_observabilidade.py`
- [x] Padrões semânticos do classificador: `tests/test_classifier.py`
- [ ] Leitura de print e de link com texto extraído
- [ ] `low_coverage` calibrado e usado na decisão
- [ ] Ampliar a base com composição de alimentos

## Decisões
| Decisão | Por quê | Onde |
|---|---|---|
| Veredito vem do score por limiares 0.35 e 0.65 | Previsível e auditável, sem depender do texto da LLM | `APP/verdict.py` |
| Recusar imagem e link em vez de inventar uma frase | Evita veredito confiante sobre assunto sem relação com a entrada | `APP/model/pipeline.py` |
| Guardrails antes da busca, menor de idade primeiro | Sem serviço a oferecer, e sem custo de busca ou LLM | `APP/model/pipeline.py` |
| Citação validada contra os chunks recuperados | Estudo inventado indica que a afirmação ligada a ele também pode ser | `APP/model/generator.py` |
| Fallback local determinístico | A API responde mesmo sem LLM | `APP/model/resposta_local.py` |
| Modelo próprio antes dos externos, dado sensível só nele | LGPD e Docs/Ethics/02 | `APP/model/llm.py` |
| Prompt `rag-v2.2` com `evidencia_suficiente` | Trechos recuperados que não tratam da pergunta não viram veredito | `APP/model/prompts.py` |
| `sem_evidencia` não lista fontes | Listar trechos fora do assunto daria cara de certeza | `APP/model/pipeline.py` |
| Classificador semântico ligado ao pipeline | Evita concentração de scores em cautela para mitos conhecidos | `APP/model/classifier.py` |
| TBCA com `aceitar_sem_evidencia=False` | A tabela é dado direto, não estudo a ser julgado | `APP/model/pipeline.py` |

## Riscos e limitações conhecidas
- A base cobre pouco de composição de alimentos. Perguntas fora dela caem em `sem_evidencia`.
- O `low_coverage` é calculado e só logado. O limiar 0.75 não foi calibrado.
- O veredito depende do `risk_score` informado pela LLM e do classificador, que são heurísticos. Mitos fora dos padrões podem ficar em `cautela`.
- Print e link não são lidos. O usuário precisa digitar a dúvida.
- O fallback local é seguro, mas mais pobre que a resposta da LLM.
- A busca depende do Supabase e da API de embeddings. Se caírem, a resposta é 503.

## Referências
- [Métricas e avaliação](../../Model/01_metricas_e_avaliacao.md)
- [Arquitetura NLP e RAG](../../Model/02_arquitetura_nlp_rag.md)
- [LLM próprio com Ollama](../../Model/05_llm_proprio_ollama.md)
- [Segurança e anti-alucinação](../../Ethics/01_seguranca_e_anti_alucinacao.md)
- [Grupos de risco e filtros](../../Ethics/02_grupos_de_risco_e_filtros.md)
- [Plataforma e deploy, contrato da API (seção 2)](../../Production/01_plataforma_e_deploy.md)
- Issues: #7, #8, #9, #10, #11, #12, #38, #39, #40
- PRs: #14, #15, #42, #43, #44, #45, #61, #62
