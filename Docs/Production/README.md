# 🚀 Produção (Production)

Este diretório concentra as diretrizes de arquitetura de software, deploy, monitoramento contínuo (MLOps), escalabilidade e gestão de custos da aplicação.

**Responsável:** João Pedro Araújo de Freitas Lyra

---

## 📌 Guiding Questions do Tema

| Pergunta | Prioridade | Status | Documento de Referência |
| :--- | :--- | :--- | :--- |
| **GQ-Production 1:** Em qual canal ou plataforma o produto será disponibilizado? | 🟢 Responder já | ✅ Respondido | [01_plataforma_e_deploy.md](./01_plataforma_e_deploy.md) |
| **GQ-Production 2:** Como será feito o monitoramento e a atualização contínua do modelo em produção? | 🟡 Planejar | ✅ Respondido | [02_monitoramento_e_mlops.md](./02_monitoramento_e_mlops.md) |
| **GQ-Production 3:** Quais são os requisitos de escalabilidade e desempenho esperados? | 🔵 Se sobrar tempo | ✅ Respondido | [03_escalabilidade_e_desempenho.md](./03_escalabilidade_e_desempenho.md) |

---

## 🧭 Decisões-Chave da Frente

| Decisão | Escolha | Documento |
| :--- | :--- | :--- |
| Canal de entrega | Aplicativo mobile (React Native + Expo) consumindo API REST | 01 |
| Estilo de arquitetura | Monólito modular em FastAPI — microsserviços não se pagam no escopo do MVP | 01 |
| Hospedagem | Render/Fly.io (backend) + Supabase (dados e RAG) | 01 |
| Controle de qualidade no deploy | *Quality gate* de RAGAS no CI: sem métrica mínima, sem merge | 01 |
| Detecção de drift | Similaridade máxima de recuperação < 0,75 = consulta sem cobertura | 02 |
| Meta de latência | TTFT < 1,5 s e resposta completa < 5 s (p95), com streaming | 03 |
| Custo estimado do MVP | ≈ US$ 14/mês para 18 mil requisições, com 35% de acerto de cache | 03 |

---

## 📁 Estrutura de Documentos

1. [**01_plataforma_e_deploy.md**](./01_plataforma_e_deploy.md)
   - Arquitetura em monólito modular e fluxo completo de uma requisição de checagem.
   - Especificação dos endpoints REST da API (`/api/v1/check-claim`, `/api/v1/feedback`, `/api/v1/profile`, `/health`), com payloads e códigos de erro.
   - Ambientes, estratégia de CI/CD com *quality gate* de avaliação e gestão de segredos.

2. [**02_monitoramento_e_mlops.md**](./02_monitoramento_e_mlops.md)
   - Estrutura de logs de inferência, latência e custo por token.
   - Detecção de *Data Drift*, *Concept Drift* e degradação silenciosa de qualidade.
   - Feedback loop (avaliação de utilidade pelo usuário e re-anotação).
   - Versionamento de código, prompt, base RAG e modelo; rotina operacional.

3. [**03_escalabilidade_e_desempenho.md**](./03_escalabilidade_e_desempenho.md)
   - SLAs de latência e orçamento de latência por etapa do pipeline.
   - Cache semântico para mitigar chamadas repetidas ao LLM.
   - Gestão de custos por requisição e limites de consumo (*Rate Limiting*).

---

## 🛠️ Estado da Implementação

A frente saiu do papel: o esqueleto da API esta em `APP/`, com testes em `tests/` e CI em `.github/workflows/ci.yml`. A tabela abaixo liga cada decisao documentada ao codigo que a implementa.

| Decisao documentada | Onde vive no codigo | Estado |
| :--- | :--- | :--- |
| Contrato REST (`/check-claim`, `/feedback`, `/profile`, `/health`) | `APP/schemas.py`, `APP/routers/` | ✅ Contrato congelado, resposta de `/check-claim` mockada |
| Formato de erro `{"error", "detail"}` | `APP/errors.py` | ✅ |
| Limiares 0.35 / 0.65 → veredito | `APP/verdict.py` | ✅ |
| Autenticação Bearer | `APP/auth.py` | ⚠️ Stub: exige o header, ainda não valida o JWT |
| Log estruturado, um por requisição | `APP/observability.py`, `APP/middleware.py` | ✅ |
| `trace_id` no log, no header e no corpo | `APP/middleware.py` | ✅ |
| Nenhum dado de saúde em log | `APP/observability.py` + testes | ✅ |
| Rate limiting por usuário/IP | `APP/ratelimit.py` | ✅ Contador em memória |
| Consentimento LGPD para dados clínicos | `APP/schemas.py`, `APP/model/repositorio.py` | ✅ |
| Persistência de perfil e feedback | `APP/model/repositorio_perfil.py`, `APP/model/repositorio_feedback.py` | ⚠️ Stub em memória, some no restart |
| Container e ambiente local | `Dockerfile`, `docker-compose.yml` | ✅ |
| Esteira de CI (lint, testes, build) | `.github/workflows/ci.yml` | ✅ |
| Pipeline de RAG | — | ❌ Depende das frentes de Dados e Modelo |
| Cache semântico | — | ❌ Depende dos embeddings |
| Quality gate de RAGAS no CI | — | ❌ Depende do benchmark de 50 perguntas |

### Como rodar localmente

```bash
cp .env.example .env      # preencha SUPABASE_URL e SUPABASE_KEY
docker compose up --build # API em http://localhost:8000
```

Sem Docker:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn APP.main:app --reload
pytest -q
```

A documentação interativa gerada pelo FastAPI fica em `http://localhost:8000/docs` — é a forma mais rápida de o pessoal do app conferir o contrato.

### Ordem sugerida dos próximos incrementos

1. **Validar o JWT do Supabase de verdade** em `APP/auth.py` (não depende de ninguém).
2. **Trocar o repositório em memória por Supabase**, assim que a frente de Dados publicar o schema de `profiles` e `feedback`.
3. **Ligar a recuperação no pgvector** em `/check-claim`, substituindo a resposta mockada — o primeiro pedaço do pipeline que produz valor real.
4. **Geração ancorada + guardrails**, com a frente de Ética.
5. **Cache semântico e quality gate de RAGAS**, que só fazem sentido depois que o pipeline existe.

---

## 🔗 Dependências entre Frentes

* **Modelo:** os limiares 0.35/0.65 e as métricas RAGAS alimentam, respectivamente, o campo `verdict` da API e o *quality gate* do CI.
* **Dados:** o schema `sources` / `articles` / `chunks` define o que a camada de recuperação consulta; a tabela `feedback` precisa ser criada em conjunto.
* **Ética:** o texto do campo `disclaimer` e os filtros de grupo de risco são aplicados pelos *guardrails* antes da resposta ser liberada.
* **Usuário:** a escolha do app mobile determina o formato da API e as metas de latência percebida.
