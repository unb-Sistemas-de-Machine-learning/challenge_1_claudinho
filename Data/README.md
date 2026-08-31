# 🗄️ Dados (Data)

Este diretório concentra a documentação, modelagem e decisões técnicas relacionadas à ingestão, armazenamento e gestão de dados do projeto.

**Responsável:** Beatriz

---

## 📌 Guiding Questions do Tema

| Pergunta | Classificação | Responsável | Tarefa / Resposta | Documento de Referência |
| :--- | :--- | :--- | :--- | :--- |
| **1. Qual(is) tipo(s) de dados vamos usar?** | Responder já | Beatriz | Sexo, Altura, Peso, Doenças, Idade, Restrições Alimentares, Rotina. | [01_tipos_e_fontes_de_dados.md](./01_tipos_e_fontes_de_dados.md) |
| **2. Onde vamos guardar eles? (SQL, JSON)** | Planejar | Beatriz | Utilizaremos SQL pela segurança dos dados. | [02_armazenamento_e_estrutura.md](./02_armazenamento_e_estrutura.md) |
| **3. Qual a fonte dos dados? (portais, pesquisas, etc.)** | Responder já | Beatriz | Artigos científicos brasileiros relacionados à nutrição, dietas extremas, transtornos alimentares, e dietas voltadas a problemas de saúde. | [01_tipos_e_fontes_de_dados.md](./01_tipos_e_fontes_de_dados.md) |

---

## 📁 Documentos

1. [**01_tipos_e_fontes_de_dados.md**](./01_tipos_e_fontes_de_dados.md)
   * Formatos de dados para o perfil (tabular em Supabase).
   * Formatos de dados para treinamento (OCR/Web scraping, metadados e conteúdo em Supabase).
   * Fontes: Artigos científicos brasileiros no Web of Science e redes sociais.

2. [**02_armazenamento_e_estrutura.md**](./02_armazenamento_e_estrutura.md)
   * Hospedagem no Supabase (PostgreSQL) com `pgvector`.
   * Tabelas `sources`, `articles` e `chunks`.
   * Decisões de design de dados e RAG.
