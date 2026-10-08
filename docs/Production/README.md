# Produção (Production)

Este diretório concentra as diretrizes de arquitetura de software, deploy, monitoramento contínuo (MLOps), escalabilidade e gestão de custos da aplicação.

**Responsável:** João Pedro Araújo de Freitas Lyra

---

## Guiding Questions do Tema

| Pergunta | Prioridade | Status | Documento de Referência |
| :--- | :--- | :--- | :--- |
| **GQ-Production 1:** Em qual canal ou plataforma o produto será disponibilizado? | 🟢 Responder já | ✅ Respondido | [01_plataforma_e_deploy.md](./01_plataforma_e_deploy.md) |
| **GQ-Production 2:** Como será feito o monitoramento e a atualização contínua do modelo em produção? | 🟡 Planejar | ✅ Respondido | [02_monitoramento_e_mlops.md](./02_monitoramento_e_mlops.md) |
| **GQ-Production 3:** Quais são os requisitos de escalabilidade e desempenho esperados? | 🔵 Se sobrar tempo | ✅ Respondido | [03_escalabilidade_e_desempenho.md](./03_escalabilidade_e_desempenho.md) |

---

## Decisões-Chave da Frente

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

## O que já está implementado na API

O código vive em `APP/`. O `/check-claim` ainda responde **mockado**: o contrato está congelado e o pipeline de RAG entra depois.

| Item | Onde está | Status |
| :--- | :--- | :--- |
| Contrato REST de `/check-claim`, `/feedback` e `/profile` | `APP/schemas.py`, `APP/routers/` | ✅ Completo, com `/check-claim` mockado |
| Autenticação por JWT do Supabase Auth | `APP/auth.py` | ✅ Valida assinatura, expiração e audiência |
| Trava de configuração na subida | `APP/auth.py`, `APP/main.py` | ✅ Não sobe fora do local sem o segredo do JWT e sem as origens do CORS |
| CORS para o app publicado | `APP/main.py`, `ORIGENS_PERMITIDAS` | ✅ Completo |
| Rate limiting por identidade | `APP/ratelimit.py` | ✅ 10/min no `/check-claim` e 30/min nas escritas, aplicado antes da autenticação |
| Log estruturado de inferência | `APP/observabilidade.py`, `APP/middleware.py` | ✅ Um registro por requisição, costurado pelo `trace_id` |
| Consentimento LGPD para dado clínico | `APP/schemas.py` (`Profile`) | ✅ Validado na entrada, antes de persistir |
| Persistência de feedback e perfil | `APP/repositorios/` | ⚠️ Em memória: as tabelas `feedback` e `profiles` ainda não existem no Supabase |
| Pipeline de RAG | ainda não existe | ⛔ Próxima frente, junto com a frente de Modelo |
| Langfuse e Sentry | ainda não existe | ⛔ Depende do pipeline estar de pé |

### Próximos incrementos

1. Criar as tabelas `feedback` e `profiles` no Supabase com a frente de Dados, e trocar as implementações em memória (o passo a passo está no docstring de cada repositório).
2. Ligar o pipeline real no `/check-claim`: cache semântico, extração de claim, busca no `pgvector`, geração ancorada e *guardrails*.
3. *Quality gate* de RAGAS no CI, quando o benchmark de 50 perguntas existir.
4. Trocar o contador de rate limit em memória pelo Redis do Upstash quando houver mais de uma instância.

---

## Estrutura de Documentos

1. [**01_plataforma_e_deploy.md**](./01_plataforma_e_deploy.md)
    - Arquitetura em monólito modular e fluxo completo de uma requisição de checagem.
    - Especificação dos endpoints REST da API (`/api/v1/check-claim`, `/api/v1/feedback`, `/api/v1/profile`, `/api/v1/health`), com payloads e códigos de erro.
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

## Dependências entre Frentes

* **Modelo:** os limiares 0.35/0.65 e as métricas RAGAS alimentam, respectivamente, o campo `verdict` da API e o *quality gate* do CI.
* **Dados:** o schema `sources` / `articles` / `chunks` define o que a camada de recuperação consulta; a tabela `feedback` precisa ser criada em conjunto.
* **Ética:** o texto do campo `disclaimer` e os filtros de grupo de risco são aplicados pelos *guardrails* antes da resposta ser liberada.
* **Usuário:** a escolha do app mobile determina o formato da API e as metas de latência percebida.
