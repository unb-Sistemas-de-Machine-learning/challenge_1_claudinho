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