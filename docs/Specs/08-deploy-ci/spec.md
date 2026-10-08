# Spec: Deploy, CI e fluxo de trabalho

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema

O projeto tem uma API FastAPI, um PWA, serviços de modelo e um scraper, mantidos por um grupo pequeno. Sem regras claras, código quebrado chega à demo, a publicação depende de passos manuais e o teto de tempo da função na nuvem pode não fechar com os timeouts do código (issue #40).

## Objetivo

Garantir que só entre nas branches principais código que passou nas checagens automáticas, publicar API e front de forma repetível e documentar como rodar tudo localmente.

## Escopo

### Dentro

- CI no GitHub Actions: API, web e build da imagem Docker.
- Proteção das branches `main` e `Dev` por ruleset.
- Deploy da API como função Python e do front como projeto separado na Vercel.
- Publicação da documentação (mkdocs) no GitHub Pages.
- Execução mensal do scraper de artigos.
- Dockerfile e `docker-compose.yml` para ambiente local.
- Serviços de LLM e embeddings em `deploy/`.

### Fora (e por quê)

- Job de deploy dentro do CI: proposto nos PRs #59 e #60 e removido. A integração Git da Vercel já publica a partir da `Dev`.
- Prévia (preview) por PR: a integração atual publica só a partir da `Dev`.
- Orquestração em contêineres em produção: a plataforma escolhida é a Vercel (ver `Docs/Production/01_plataforma_e_deploy.md`).
- Monitoramento de produção além do log estruturado: tratado em `Docs/Production/02_monitoramento_e_mlops.md`.

## Requisitos funcionais

- RF-01: todo push e PR para `main` e `Dev` dispara o workflow `CI`.
- RF-02: o job da API roda black, ruff e pytest.
- RF-03: o job do web roda oxlint, prettier, vitest e o build.
- RF-04: um job constrói a imagem Docker da API.
- RF-05: a `Dev` só aceita merge por PR com os checks "Lint e testes (API)" e "Lint e testes (web)" verdes.
- RF-06: a `main` só aceita merge por PR com 1 aprovação, revisões antigas descartadas em novo push e os três checks verdes (API, web e Docker).
- RF-07: a API é exposta na Vercel por `api/index.py`, que apenas importa `app` de `APP.main`.
- RF-08: o front é um projeto separado, com `web/vercel.json` reescrevendo todas as rotas para `/index.html` (fallback de SPA).
- RF-09: o workflow `docs.yml` compila o mkdocs e publica no GitHub Pages em push na `main` ou `Dev`.
- RF-10: o workflow `article_scraper.yml` roda no dia 1 de cada mês e também manualmente.
- RF-11: `docker-compose.yml` sobe API (porta 8000) e web (porta 5173) localmente.
- RF-12: o front lê `VITE_SUPABASE_URL` e `VITE_SUPABASE_ANON_KEY` no build; a chave `service_role` nunca vai para o front.

## Requisitos não funcionais

- Tempo: `maxDuration` de 300 s na função da API, alinhado à cadeia de timeouts (PR #45, issue #40).
- Tamanho: a API sem o modelo de embeddings cabe no limite de função da Vercel; `excludeFiles` tira testes, docs, benchmarks e `deploy/` do pacote.
- Segredos: ficam nas variáveis de ambiente da Vercel e do GitHub, nunca no repositório.
- Repetibilidade: as mesmas checagens rodam local e no CI (`requirements-dev.txt`, `npm ci`).
- Idioma: documentação e mensagens de commit em português.

## Critérios de aceite

- [x] CI com API, web e Docker: `.github/workflows/ci.yml`.
- [x] Ruleset da `Dev` ativo, sem aprovação obrigatória, com 2 checks exigidos (API e web).
- [x] Ruleset da `main` ativo, 1 aprovação, dismiss de revisões antigas, 3 checks exigidos.
- [x] Teto de 300 s e exclusões de pacote: `vercel.json`.
- [x] Entrada ASGI da API: `api/index.py`.
- [x] Fallback de SPA do front: `web/vercel.json`.
- [x] Publicação da documentação: `.github/workflows/docs.yml`.
- [x] Scraper mensal: `.github/workflows/article_scraper.yml`.
- [x] Ambiente local com Docker: `Dockerfile`, `docker-compose.yml`, `web/Dockerfile`.
- [x] Serviços de modelo: `deploy/ollama-space`, `deploy/ollama-azure`, `deploy/embeddings-space`.
- [x] PWA com atualização automática: `registerType: 'autoUpdate'` em `web/vite.config.ts`.
- [ ] Prévia por PR na Vercel.
- [ ] Deploy automatizado e verificado pelo CI (smoke test pós-deploy).
- [ ] Release da `Dev` para a `main` concluída (PR #58 aberto na data deste documento).

## Decisões

| Decisão | Por quê | Onde |
|---|---|---|
| Duas branches protegidas, `Dev` para integração e `main` para release | A `Dev` fica ágil (sem aprovação), a `main` exige revisão | Rulesets "Protecao da Dev" e "Protecao da main" |
| Sem push direto, nem para admin | O ruleset está ativo e vale para todos | Rulesets do GitHub |
| API como função Python e front como projeto separado | Cada parte tem build e variáveis próprias | `vercel.json`, `web/vercel.json` |
| Deploy pela integração Git da Vercel, sem job no CI | Evita duplicar a publicação e guardar token no CI | PRs #59 e #60 |
| `maxDuration` 300 | Cobre o cold start do Ollama dentro do limite do plano | `vercel.json`, PR #45, issue #40 |
| Embeddings fora da função da API | Mantém a função pequena | `deploy/embeddings-space` |
| Docker apenas como ambiente local e checagem de build | A produção roda na Vercel | `Dockerfile`, `docker-compose.yml` |
| PWA com `autoUpdate` | Quem abriu o app recebe a versão nova no acesso seguinte | `web/vite.config.ts` |

## Riscos e limitações conhecidas

- Sem prévia por PR: só se vê o resultado depois do merge na `Dev`.
- Variáveis `VITE_*` entram no build: mudar exige novo deploy do front.
- PWA já instalado mostra a versão antiga até recarregar uma vez; recarregar antes da demo.
- Pasta do repositório sincronizada trava pytest, vitest e git em operações pesadas: rodar testes numa cópia fora dela.
- Cold start do Ollama pode consumir boa parte dos 300 s.
- O plano Hobby da Vercel limita a duração e o uso da função.
- O CI não valida o deploy em si.

## Referências

- `.github/workflows/ci.yml`, `docs.yml`, `article_scraper.yml`
- `vercel.json`, `web/vercel.json`, `api/index.py`
- `Docs/Production/01_plataforma_e_deploy.md`, `Docs/Production/03_escalabilidade_e_desempenho.md`
- `Docs/Model/05_llm_proprio_ollama.md`, `deploy/README.md`
- `web/CONTRIBUTING.md`
- Issues #35, #38, #40; PRs #45, #58, #59, #60
