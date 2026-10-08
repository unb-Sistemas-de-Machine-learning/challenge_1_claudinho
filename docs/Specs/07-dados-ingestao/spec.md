# Spec: Base de conhecimento (dados, ingestão e atualização)

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema

O Claudinho só pode afirmar algo sobre uma alegação de nutrição se houver estudo científico para sustentar. Sem uma base própria, indexada e atualizada, a API teria de confiar no que o LLM "sabe", o que gera resposta sem fonte. Além disso, a base precisa ser alimentada sem expor chave de escrita no app público.

## Objetivo

Manter no Supabase uma base de estudos científicos pesquisável por similaridade semântica, alimentada por duas rotas (PDFs locais e coleta mensal do PubMed), com a escrita restrita a quem tem a `service_role`.

## Escopo

### Dentro

- Schema no Supabase Postgres com `pgvector`: `sources`, `articles`, `chunks` (e `users`, fora desta spec).
- Função de busca `buscar_chunks` (em `migracao_chunks.sql`), consumida pela API via RPC.
- Ingestão local de PDFs (`ingerir_pdf.py`): extrai texto, divide em chunks, gera embeddings e grava.
- Coleta automática do PubMed (`scraper/fetch_pubmed.py`) em workflow do GitHub Actions.
- Embeddings `intfloat/multilingual-e5-base` (768 dimensões), com Space próprio para a consulta em produção.
- Consulta à tabela `TBCA` (composição de alimentos) pelo retriever.
- RLS nas tabelas de conhecimento: leitura pública, escrita só pela `service_role`.

### Fora (e por quê)

- Classificador de risco treinado (`APP/model/train.py`): gera um `.joblib` que não é usado em produção. Em uso está o classificador por regras (`APP/model/classifier.py`). Fica registrado como experimento.
- Carga da TBCA por script versionado: a tabela é lida pelo código, mas não há rotina de ingestão dela neste repositório.
- Coleta de texto completo no PubMed: o scraper guarda só título, resumo e metadados.
- Ingestão de posts de redes sociais: o schema prevê, mas nenhuma rotina existe.
- Calibração do limiar de baixa cobertura: não houve dados de uso real.

## Requisitos funcionais

- RF-01: a busca por similaridade devolve os chunks mais próximos da consulta, já com o título do artigo, via `buscar_chunks`.
- RF-02: a ingestão de PDF grava `sources`, `articles` e `chunks` com embeddings de 768 dimensões.
- RF-03: o mesmo PDF não é ingerido duas vezes (hash `sha256` em `articles.metadata`).
- RF-04: o PDF é dividido em janelas de 350 palavras com 70 de sobreposição, descartando sobras com menos de 20 palavras.
- RF-05: `ingerir_pdf.py` tem modo `--dry-run`, que só inspeciona sem gravar.
- RF-06: o scraper consulta o PubMed por `"nutrition"[MeSH Terms] OR "physical fitness"[MeSH Terms]`, restrito aos últimos 5 anos, com até 5000 IDs.
- RF-07: o scraper busca detalhes em lotes de 50, com até 3 tentativas e espera exponencial.
- RF-08: o scraper ignora artigos sem resumo e artigos já existentes (por DOI ou, sem DOI, por URL).
- RF-09: o scraper reaproveita `dividir_em_chunks`, `gerar_embeddings` e `gravar_chunks` de `ingerir_pdf.py`.
- RF-10: o workflow roda todo dia 1º às 04:00 UTC e sob demanda (`workflow_dispatch`).
- RF-11: o scraper encerra com erro se `SUPABASE_URL` ou a chave não estiverem definidas.
- RF-12: o retriever marca `low_coverage` quando não há chunk ou a maior similaridade fica abaixo de 0.75.
- RF-13: o embedding da consulta usa o prefixo `query: ` exigido pelo e5 e recusa vetor de dimensão diferente de 768.

## Requisitos não funcionais

- Segurança: chave `service_role` só em variável de ambiente ou GitHub Secrets, nunca no app.
- Custo: embeddings open source, sem chave de API e sem enviar o conteúdo dos PDFs a terceiros.
- Privacidade: a ingestão local roda na máquina de quem alimenta a base.
- Reprodutibilidade: ambiente de ingestão separado (`requirements-ingestao.txt`) para não pesar o da API.
- Consistência: a dimensão do vetor no banco e no modelo devem coincidir (768).
- Resiliência: falha em um lote do PubMed não derruba a coleta inteira.

## Critérios de aceite

- [x] Função `buscar_chunks` e tabela `chunks` com índice HNSW definidas em `migracao_chunks.sql`.
- [x] Estrutura documentada em `Docs/Data/02_armazenamento_e_estrutura.md`.
- [x] Ingestão de PDF com deduplicação, `--dry-run` e metadados (`ingerir_pdf.py`).
- [x] Scraper do PubMed com workflow mensal e manual (`.github/workflows/article_scraper.yml`), entregue no PR #53 (issue #50).
- [x] Cliente de embeddings coberto por testes (`tests/test_embeddings.py`: formato do Space, prefixo, dimensão errada, provedor fora do ar).
- [x] Datas e contexto dos chunks cobertos em `tests/test_retriever.py`.
- [x] RLS ligado em `articles`, `chunks` e `sources` (leitura pública, escrita só pela `service_role`), em 06/10.
- [ ] Teste automatizado para `ingerir_pdf.py` e `scraper/fetch_pubmed.py` (não há arquivo de teste dedicado).
- [x] SQL do RLS versionado em `deploy/sql/002_rls_base_cientifica.sql`.
- [ ] Script versionado da carga da TBCA no repositório.
- [ ] Limiar de baixa cobertura (0.75) calibrado com dados reais.
- [ ] Cobertura de composição de alimentos suficiente para perguntas como "arroz com feijão é proteína completa".

## Decisões

| Decisão | Por quê | Onde |
| :--- | :--- | :--- |
| Supabase Postgres com pgvector | Banco SQL e busca vetorial no mesmo lugar | `migracao_chunks.sql` |
| `multilingual-e5-base` (768 dims) | Cobre português técnico, roda local sem custo | `ingerir_pdf.py`, `APP/model/embeddings.py` |
| Embedding de consulta em Space próprio | Evita carregar o torch na função serverless | `deploy/embeddings-space` |
| Chunks de 350 palavras, sobreposição de 70 | Aproxima 500 tokens com 100 de sobreposição em português | `ingerir_pdf.py` |
| Deduplicação por `sha256`, DOI ou URL | Reexecutar a ingestão não duplica estudos | `ingerir_pdf.py`, `scraper/fetch_pubmed.py` |
| Coleta mensal, não diária | O volume de estudos novos é baixo e a cota é limitada | `.github/workflows/article_scraper.yml` |
| Escrita só pela `service_role` | A chave pública embutida no app deixava as tabelas abertas para escrita | RLS no Supabase |
| Classificador em uso é por regras | O modelo treinado não foi para produção | `APP/model/classifier.py` |

## Riscos e limitações conhecidas

- A base cobre mais dietas da moda e desinformação do que composição de alimentos. Perguntas como "arroz com feijão é proteína completa" caem em "Faltam estudos".
- O limiar 0.75 de baixa cobertura é uma estimativa inicial, sem calibração.
- O scraper pega só resumos em inglês do PubMed, o que limita a precisão em alegações em português.
- A busca de IDs usa até 5000 resultados e termos MeSH amplos, então entram estudos de pouca relevância para alegações de internet.
- `ingerir_pdf.py` declara em seu docstring que não vai para o repositório compartilhado, mas o scraper o importa. Convém alinhar isso.
- O modelo treinado (`classificador_risco.joblib`) é experimento e pode divergir das regras em uso.
- O README do scraper e a migração dependem de execução manual no SQL Editor do Supabase.

## Referências

- `Docs/Data/01_tipos_e_fontes_de_dados.md`
- `Docs/Data/02_armazenamento_e_estrutura.md`
- `Docs/Model/04_treinamento_e_classificador_risco.md`
- `scraper/README.md`
- Issue #50 e PR #53 (scraper do PubMed)
