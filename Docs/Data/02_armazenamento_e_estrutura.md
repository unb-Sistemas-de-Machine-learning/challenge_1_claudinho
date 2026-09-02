# Estrutura do Banco de Dados e Armazenamento

> **Referência:** GQ-Data 2  
> **Responsável:** Beatriz  

---

## 1. Armazenamento

* **Tecnologia:** Utilizaremos SQL pela segurança dos dados.
* **Hospedagem:** O banco de dados é hospedado no **Supabase (PostgreSQL)** com a extensão `pgvector` habilitada para busca por similaridade (RAG).

---

## 2. Estrutura das Tabelas

### 2.1. Tabela `sources` — Origem do conteúdo

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | uuid PK | Identificador único |
| `name` | text | Nome da fonte (ex: "Web of Science", "Instagram") |
| `type` | enum | `scientific` / `social_media` / `news` |
| `reliability` | int | Score de confiabilidade da fonte (útil como feature) |

---

### 2.2. Tabela `articles` — Dados de treinamento

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | uuid PK | Identificador único |
| `source_id` | uuid FK → sources | Referência à fonte |
| `title` | text | Título do conteúdo |
| `content` | text | Texto completo extraído |
| `url` | text | URL original |
| `author` | text | Autor |
| `published_at` | timestamp | Data de publicação original |
| `collected_at` | timestamp | Data da coleta (scraping) |
| `content_type` | enum | `article` / `post` / `video_transcript` |
| `label` | enum | `true` / `fake` / `misleading` / `unlabeled` |
| `label_confidence` | float | Grau de certeza da rotulagem |
| `labeled_by` | text | Quem rotulou (pessoa ou método) |
| `language` | text | Idioma (padrão `pt-BR`) |
| `metadata` | jsonb | Campo flexível para DOI, palavras-chave, nome do periódico, etc. |

---

### 2.3. Tabela `chunks` — Fragmentos para RAG

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | uuid PK | Identificador único |
| `article_id` | uuid FK → articles | Referência ao artigo |
| `chunk_index` | int | Ordem do fragmento dentro do artigo |
| `content` | text | Texto do fragmento |
| `embedding` | vector(1536) | Vetor de embedding para busca por similaridade (pgvector) |

---

## 3. Decisões de Design

* **`chunks` separado de `articles`:** RAG recupera fragmentos de texto, não artigos inteiros. Cada artigo é dividido em janelas de ~500 tokens com sobreposição de ~100 tokens.
* **`label` com mais de 2 valores:** Muita desinformação nutricional é *misleading* (estudo real, conclusão errada) e não totalmente fabricada. `unlabeled` permite dados ainda não revisados.
* **`label_confidence` e `labeled_by`:** Rastreia a procedência da rotulagem para filtrar rótulos de baixa qualidade e medir concordância entre anotadores.
* **`metadata` como jsonb:** Artigos científicos têm DOI, palavras-chave, periódico; posts de redes sociais têm curtidas, compartilhamentos, hashtags. Um campo JSON flexível evita poluição do schema.
