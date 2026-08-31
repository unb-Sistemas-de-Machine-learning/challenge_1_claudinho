# 🤖 Modelo (Model)

Este diretório concentra a modelagem de Machine Learning e Processamento de Linguagem Natural (NLP), arquitetura de RAG, métricas de avaliação e técnicas de mitigação de alucinação.

**Responsável:** Ana Luiza Hoffmann Ferreira

---

## 📌 Guiding Questions do Tema

| Pergunta | Prioridade | Documento de Referência |
| :--- | :--- | :--- |
| **GQ-Model 1:** Quais métricas de avaliação serão priorizadas para lidar com os riscos de falsos positivos e falsos negativos? | 🟡 Planejar | [01_metricas_e_avaliacao.md](./01_metricas_e_avaliacao.md) |
| **GQ-Model 2:** Qual será a arquitetura e a abordagem de NLP utilizada para garantir respostas baseadas em evidências e evitar "alucinações"? | 🟡 Planejar | [02_arquitetura_nlp_rag.md](./02_arquitetura_nlp_rag.md) |
| **GQ-Model 3:** Como o modelo processará a "linguagem da internet" e diferentes formatos de entrada? | 🟡 Planejar | [03_processamento_linguagem_internet.md](./03_processamento_linguagem_internet.md) |

---

## 📁 Estrutura de Documentos

1. [**01_metricas_e_avaliacao.md**](./01_metricas_e_avaliacao.md)
   - Análise de impacto de Falsos Positivos e Falsos Negativos no domínio da saúde alimentar.
   - Definição de métricas de classificação e calibração de _threshold_.
   - Métricas específicas de RAG.

2. [**02_arquitetura_nlp_rag.md**](./02_arquitetura_nlp_rag.md)
   - Pipeline de *Retrieval-Augmented Generation* (RAG).
   - Modelos de embeddings semânticos para pt-BR e estratégias de *Chunking* / *Reranking*.
   - Técnicas de *Grounded Generation* e prompts anti-alucinação.

3. [**03_processamento_linguagem_internet.md**](./03_processamento_linguagem_internet.md)
   - Extração de alegações factuais (*Claim Extraction*) a partir de posts informais.
   - Tratamento de sarcasmo, ironia, gírias nutricionais e jargões populares.
   - Exemplos de *Few-Shot Prompting* e normalização textual.
