# 🚀 Produção (Production)

Este diretório concentra as diretrizes de arquitetura de software, deploy, monitoramento contínuo (MLOps), escalabilidade e gestão de custos da aplicação.

**Responsável:** João Pedro Araújo de Freitas Lyra

---

## 📌 Guiding Questions do Tema

| Pergunta | Prioridade | Documento de Referência |
| :--- | :--- | :--- |
| **GQ-Production 1:** Em qual canal ou plataforma o produto será disponibilizado? | 🟢 Responder já | [01_plataforma_e_deploy.md](./01_plataforma_e_deploy.md) |
| **GQ-Production 2:** Como será feito o monitoramento e a atualização contínua do modelo em produção? | 🟡 Planejar | [02_monitoramento_e_mlops.md](./02_monitoramento_e_mlops.md) |
| **GQ-Production 3:** Quais são os requisitos de escalabilidade e desempenho esperados? | 🔵 Se sobrar tempo | [03_escalabilidade_e_desempenho.md](./03_escalabilidade_e_desempenho.md) |

---

## 📁 Estrutura de Documentos

1. [**01_plataforma_e_deploy.md**](./01_plataforma_e_deploy.md)
   - Arquitetura de microsserviços/servidores.
   - Especificação dos endpoints REST da API (`/api/v1/check-claim`, `/api/v1/feedback`, `/api/v1/profile`).
   - Estratégia de CI/CD e esteira de deploy contínuo.

2. [**02_monitoramento_e_mlops.md**](./02_monitoramento_e_mlops.md)
   - Estrutura de logs de inferência, latência e custo por token.
   - Detecção de *Data Drift* e surgimento de novos mitos nutricionais nas redes.
   - Feedback loop (avaliação de utilidade pelo usuário e re-anotação).

3. [**03_escalabilidade_e_desempenho.md**](./03_escalabilidade_e_desempenho.md)
   - SLAs de latência.
   - Cache semântico para mitigar chamadas repetidas ao LLM.
   - Gestão de custos por requisição e limites de consumo (*Rate Limiting*).
