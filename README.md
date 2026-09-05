# Challenge 1

## 📍 Objetivo
O primeiro *challenge* visa desenvolver um sistema de *Machine Learning* capaz de identificar Fake News. O desafio é dividido em **Engage**, **Investigate** e **Act**. Cada parte do desafio é dividido pelas aulas ministradas segundas e quartas, do dia **12/08** até **07/10**.

## 🦾 Devs

| Nome                              | Matrícula | Github           |
|-----------------------------------|-----------|------------------|
| Ana Luiza Hoffmann Ferreira       | 202015901 | AnHoff           |
| Beatriz Brandão Fidelis Batista   | 242005202 | beatrizbranfb    |
| João Pedro Araújo de Freitas Lyra | 232003661 | jadequilin       |
| Matheus Moreira Lopes Perillo     | 190093421 | matheusperillo03 |
| Maria Clara de Freitas Pina       | 232021900 | mariapinaclara   |
   
## 🗓️ Agenda

- **12/08:** Big Idea and Essential Questions
- **17/08:** Challenge Statement
- **19/08:** Guiding Questions
- **24/08:** Fontes e formatos de dados
- **26/08:** Ingestão e preparação de dados + análise exploratória
- **31/08:** Amostragem e rotulagem dos dados do desafio
- **02/09:** Classes desbalanceadas e data augmentation
- **07/09:** Feriado — Independência do Brasil
- **09/09:** Engenharia de features + prevenção de data leakage
- **14/09:** Baselines e seleção de modelos candidatos
- **16/09:** Treino, depuração e iteração de modelos
- **21/09:** Métricas e avaliação "offline" + documentação de experimentos
- **23/09:** Servindo o modelo como API (deploy simples, mitos de deploy)
- **28/09:** Integração da solução + versionamento de código, dados e modelos
- **30/09:** Viés, limitações e IA responsável na solução do grupo
- **05/10:** Demo interna + "feedback" entre grupos + preparação da entrega
- **07/10:** Apresentação final do Desafio 1 (audiência real)

---

# Desenvolvimento

## 📌 Guiding Questions

Em primeiro momento, foram levantadas as *Guiding Questions* (Questões-Guia) para determinar os objetivos e os meios que utilizaremos para alcançá-los. As questões podem ser conferidas no documento [GQ.md](./Docs/GQ.md) e contam com classificação e responsável.

A partir do documento citado, foi criada a estrutura básica deste repositório, visando responder a cada tema de forma organizada. As respostas para cada tipo de pergunta estão organizadas conforme se segue.

### 🗄️ [Dados](./Docs/Data/README.md)
* **Responsável:** Beatriz Brandão Fidelis Batista
* [01 - Tipos de Dados](./Docs/Data/01_tipos_e_fontes_de_dados.md): Mapeamento de dados tabulares de usuários.
* [02 - Armazenamento e Modelagem](./Docs/Data/02_armazenamento_e_estrutura.md): Schema relacional e vetorial no PostgreSQL/Supabase com extensão `pgvector`.
* [03 - Fontes de Dados](./Docs/Data/01_tipos_e_fontes_de_dados.md): Mapeamento de bases científicas (SciELO, Web of Science, MS) e claims de desinformação.

### 👤 [Usuário](./Docs/User/README.md)
* **Responsável:** Beatriz Brandão Fidelis Batista
* [01 - Personas do MVP](./Docs/User/01_personas.md): Personas principais e secundárias, dores com terrorismo nutricional e mapa de empatia.
* [02 - Acesso e Canais](./Docs/User/02_acesso_e_canais.md): Plataforma de acesso e modos de entrada de dúvidas/links.
* [03 - Proposta de Valor e Pitch](./Docs/User/03_proposta_de_valor_pitch.md): Elevator pitch em 30 segundos, comparativo de diferenciais e *Value Proposition Canvas*.

### 🤖 [Modelo](./Docs/Model/README.md)
* **Responsável:** Ana Luiza Hoffmann Ferreira
* [01 - Métricas de Avaliação e Riscos (FP vs FN)](./Docs/Model/01_metricas_e_avaliacao.md): Trade-off entre Falso Positivo e Falso Negativo, métricas prioritárias ($F_2$-Score, Recall) e métricas RAG (Ragas).
* [02 - Arquitetura de NLP e RAG](./Docs/Model/02_arquitetura_nlp_rag.md): Pipeline RAG, embeddings semânticos, grounded generation e prevenção de alucinações.
* [03 - Processamento de Linguagem da Internet](./Docs/Model/03_processamento_linguagem_internet.md): Extração de claims, tratamento de gírias nutricionais, sarcasmo e *Few-Shot Prompting*.

### 🚀 [Produção](./Docs/Production/README.md)
* **Responsável:** João Pedro Araújo de Freitas Lyra
* [01 - Plataforma e Estratégia de Deploy](./Docs/Production/01_plataforma_e_deploy.md): Arquitetura e especificação de endpoints REST (`/check-claim`, `/feedback`, `/profile`).
* [02 - Monitoramento e MLOps](./Docs/Production/02_monitoramento_e_mlops.md): Logs estruturados de inferência, detecção de *Data/Concept Drift* e feedback loop.
* [03 - Escalabilidade e Desempenho](./Docs/Production/03_escalabilidade_e_desempenho.md): SLAs de latência, *Semantic Caching* e estimativa de custos operacionais.

### ⚖️ [Ética](./Docs/Ethics/README.md)
* **Responsável:** Maria Clara de Freitas Pina
* [01 - Segurança e Protocolo Anti-Desinformação](./Docs/Ethics/01_seguranca_e_anti_alucinacao.md): Suíte de testes de estresse (*Red Teaming*) e política de recusa segura (*Safe Refusal*).
* [02 - Proteção de Grupos Vulneráveis e Filtros](./Docs/Ethics/02_grupos_de_risco_e_filtros.md): Guardrails para transtornos alimentares (TCA), gestantes e condições clínicas crônicas.
* [03 - Transparência e Disclaimers](./Docs/Ethics/03_transparencia_e_disclaimers.md): Textos padrão de disclaimers legais/médicos e rastreabilidade de fontes com DOI.

---

# 💻 Rodando a API localmente

O backend está em `APP/`. Hoje ele é um **esqueleto**: o contrato dos endpoints é o definitivo, mas `/check-claim` responde com dados **mockados**, porque o pipeline de RAG ainda não está ligado. Isso permite que o app mobile já seja desenvolvido contra o formato final da resposta.

## Pré-requisitos

* Python **3.12** (versão fixada em `.python-version`)
* Docker (opcional, para rodar do jeito que vai para produção)

## 1. Configurar as variáveis de ambiente

```bash
cp .env.example .env
```

Preencha `SUPABASE_URL` e `SUPABASE_KEY` com os valores do projeto no Supabase (*Project Settings → API*).

> ⚠️ O `.env` **nunca** entra no Git, o `.gitignore` bloqueia. Se precisar adicionar uma variável nova, adicione o **nome** dela (sem valor) no `.env.example` para o resto do time saber que ela existe.

## 2. Instalar as dependências

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## 3. Subir o servidor

```bash
uvicorn APP.main:app --reload
```

* API: http://127.0.0.1:8000
* Documentação interativa (Swagger): http://127.0.0.1:8000/docs

Teste rápido:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/api/v1/check-claim \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer qualquer-token' \
  -d '{"input_type":"text","text":"água com limão em jejum queima gordura?"}'
```

## 4. Rodar com Docker

```bash
docker compose up --build
```

## 5. Testes e qualidade

Os mesmos comandos que o CI roda a cada push e pull request:

```bash
pytest -q          # testes
ruff check .       # lint
black --check .    # formatação
```

## Estrutura

| Caminho | O que é |
| :--- | :--- |
| `APP/main.py` | Monta a aplicação FastAPI e registra as rotas |
| `APP/schemas.py` | Modelos Pydantic do contrato ([Produção 01](./Docs/Production/01_plataforma_e_deploy.md), seção 2) |
| `APP/routers/health.py` | `GET /health`, o *liveness probe* |
| `APP/routers/check_claim.py` | `POST /api/v1/check-claim`, ainda **mockado** |
| `APP/routers/feedback.py` | `POST /api/v1/feedback`, registra 👍 / 👎 sobre uma resposta |
| `APP/verdict.py` | Converte `risk_score` em veredito (limiares 0.35 / 0.65) |
| `APP/auth.py` | **Stub** de autenticação: exige o header `Bearer`, ainda não valida o JWT |
| `APP/config.py` | Variáveis de ambiente |
| `APP/observabilidade.py` | Log estruturado de inferência e contexto do `trace_id` |
| `APP/middleware.py` | Middleware que emite um registro por requisição |
| `APP/repositorios/feedback.py` | Persistência do feedback, **hoje em memória** |
| `APP/model/database.py` | Client do Supabase, criado sob demanda |
| `tests/` | Suíte do pytest |

## Logs de inferência

Cada requisição gera **uma linha JSON** no stdout, no formato da seção 3 do [Produção 02](./Docs/Production/02_monitoramento_e_mlops.md). O `trace_id` é a chave que liga o log, a resposta da API e o feedback do usuário.

```json
{"trace_id":"80d16b32-...","endpoint":"/api/v1/check-claim","user_id_hash":"sha256:1cf0...",
 "input":{"input_type":"text","raw_length":30,"language":"pt-BR"},
 "output":{"verdict":"desinformacao","risk_score":0.78,"sources_count":1},
 "generation":{"model_version":"mock@0.1.0","prompt_version":"mock-v0"},
 "performance":{"cache_hit":false,"total_latency_ms":3},"status":"success","error":null}
```

Três coisas que o log **não** registra, de propósito:

* o texto da pergunta e o comentário do feedback, que podem conter condição clínica;
* o token do usuário, que entra como `sha256:...`;
* o `/health`, porque o provedor bate nele a cada 30s e afogaria os registros de verdade.

Todo registro carrega `model_version` e `prompt_version`. É o que permite atribuir uma queda de qualidade à mudança que a causou, em vez de descobrir tarde demais que o provedor trocou o modelo por baixo dos panos.

Os blocos `nlp`, `retrieval` e `guardrails` já existem no formato, com `null`. Eles passam a ser preenchidos conforme cada etapa do pipeline de RAG for entrando.

## Feedback

`POST /api/v1/feedback` já valida e responde o contrato completo, mas **a persistência ainda é em memória**, ou seja, o feedback some quando o processo reinicia. A tabela `feedback` no Supabase ainda não existe (é o item 3 da seção 8 do Produção 02).

Quando ela existir, o único ponto a mudar é o retorno de `obter_repositorio_de_feedback`, no fim de `APP/repositorios/feedback.py`. O passo a passo completo (schema sugerido, RLS, e as duas decisões que precisam da frente de Dados e de Ética) está no docstring do `RepositorioSupabase`, no mesmo arquivo.

## O que ainda falta

- [ ] Validar de verdade o JWT do Supabase Auth (`APP/auth.py` hoje só checa se o header existe)
- [ ] Criar a tabela `feedback` no Supabase e trocar o repositório em memória
- [ ] Endpoints `GET`/`PUT /profile` (dado sensível de LGPD, precisa da frente de Ética)
- [ ] Ligar o pipeline real: cache semântico, extração de claim, busca no `pgvector`, geração e guardrails
- [ ] *Quality gate* de RAGAS no CI (depende do benchmark de 50 perguntas)
- [ ] Instrumentar com o SDK do Langfuse e o Sentry
- [ ] Rate limiting
