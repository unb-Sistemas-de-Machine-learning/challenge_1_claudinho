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
| `id` | `uuid` PK | Identificador único (`gen_random_uuid()`) |
| `name` | `text` NOT NULL | Nome da fonte (ex: "Web of Science", "Instagram") |
| `type` | `source_type` NOT NULL | Categoria da fonte (ver §2.4) |
| `reliability` | `integer` | Score de confiabilidade da fonte, 0–100 (útil como *feature*) |

---

### 2.2. Tabela `articles` — Conteúdo coletado

Guarda o texto completo de cada item coletado — artigo científico, post ou transcrição. É a base tanto para o treinamento quanto para a recuperação.

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `uuid` PK | Identificador único (`gen_random_uuid()`) |
| `source_id` | `uuid` FK → `sources` | Referência à fonte (`ON DELETE CASCADE`) |
| `title` | `text` | Título do conteúdo |
| `content` | `text` | Texto completo extraído |
| `url` | `text` | URL original |
| `author` | `text` | Autor |
| `published_at` | `timestamptz` | Data de publicação original |
| `collected_at` | `timestamptz` | Data da coleta (padrão `now()`) |
| `content_type` | `content_type` | Formato do conteúdo (ver §2.4) |
| `label` | `label_type` | Rótulo de veracidade (padrão `unlabeled`, ver §2.4) |
| `label_confidence` | `double precision` | Grau de certeza da rotulagem |
| `labeled_by` | `text` | Quem rotulou (pessoa ou método) |
| `language` | `text` | Idioma (padrão `pt-BR`) |
| `metadata` | `jsonb` | Campo flexível para DOI, palavras-chave, nome do periódico, etc. |

**Chaves usadas em `metadata` pela ingestão de PDFs:**

| Chave | Descrição |
| :--- | :--- |
| `sha256` | Hash do arquivo de origem — é o que evita ingerir o mesmo PDF duas vezes |
| `arquivo` | Nome do arquivo PDF original |
| `doi` | DOI extraído do texto, quando presente |
| `palavras_chave` | Lista extraída da seção "Palavras-chave" / "Keywords" |
| `paginas` | Número de páginas do PDF |
| `modelo_embedding` | Modelo usado para gerar os vetores dos chunks deste artigo |

---

### 2.3. Tabela `chunks` — Fragmentos para RAG

| Coluna | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `uuid` PK | Identificador único (`gen_random_uuid()`) |
| `article_id` | `uuid` FK → `articles` | Referência ao artigo (`ON DELETE CASCADE`) |
| `chunk_index` | `integer` | Ordem do fragmento dentro do artigo |
| `content` | `text` | Texto do fragmento |
| `embedding` | `vector(768)` | Vetor de embedding para busca por similaridade (pgvector) |

**Restrições e índices:**

* `UNIQUE (article_id, chunk_index)` — impede fragmentos duplicados no mesmo artigo.
* Índice **HNSW** sobre `embedding` com `vector_cosine_ops`, para busca aproximada em tempo logarítmico.
* Índice sobre `metadata ->> 'sha256'` em `articles`, para a checagem de duplicata na ingestão.

**Busca semântica:** exposta pela função `buscar_chunks(consulta vector(768), limite int, similaridade_minima float)`, que devolve os fragmentos mais próximos já com o título do artigo de origem. A API consome essa função via RPC.

---

### 2.4. Tipos enumerados

| Enum | Valores |
| :--- | :--- |
| `source_type` | `scientific` · `social_media` · `news` |
| `content_type` | `article` · `post` · `video_transcript` |
| `label_type` | `true` · `fake` · `misleading` · `unlabeled` |

---

## 3. Decisões de Design

* **`chunks` separado de `articles`:** RAG recupera fragmentos de texto, não artigos inteiros. Cada artigo é dividido em janelas de ~500 tokens com sobreposição de ~100 tokens, respeitando o limite das sentenças para que o fragmento recuperado continue legível.
* **Dois papéis na mesma tabela — como distinguir:** `articles` guarda o **corpus de evidência** (artigos científicos que fundamentam as respostas do RAG) e o **material a ser classificado** (posts de redes sociais). Os dois se separam pelos campos que já existem:

  | Papel | Filtro | `label` |
  | :--- | :--- | :--- |
  | Evidência para o RAG | `sources.type = 'scientific'` e `content_type = 'article'` | `unlabeled`, sempre |
  | Dataset rotulado | `sources.type = 'social_media'` e `content_type = 'post'` | `true` / `fake` / `misleading` |

  Artigos revisados por pares ficam **deliberadamente** como `unlabeled`: o campo `label` descreve a veracidade de uma *alegação*, e um artigo científico é o instrumento que julga alegações, não uma delas. Rotulá-los como `true` ensinaria a um classificador que registro acadêmico equivale a verdade — correlação espúria que não sobrevive a um post bem escrito.

  A função `buscar_chunks` aplica esse filtro por padrão (`apenas_cientificos = true`), para que o RAG nunca recupere um post de desinformação e o apresente como evidência.

* **`label` com mais de 2 valores:** Muita desinformação nutricional é *misleading* (estudo real, conclusão errada) e não totalmente fabricada. `unlabeled` permite dados ainda não revisados.
* **`label_confidence` e `labeled_by`:** Rastreia a procedência da rotulagem para filtrar rótulos de baixa qualidade e medir concordância entre anotadores.
* **`metadata` como jsonb:** Artigos científicos têm DOI, palavras-chave, periódico; posts de redes sociais têm curtidas, compartilhamentos, hashtags. Um campo JSON flexível evita poluição do schema.
* **`embedding` com 768 dimensões:** O schema nasceu com `vector(1536)`, a dimensão do `text-embedding-3-small` da OpenAI. Passamos a gerar os embeddings **localmente** com `intfloat/multilingual-e5-base` (768 dimensões, open source), o que elimina custo por requisição e evita enviar o conteúdo dos artigos para terceiros. A dimensão da coluna acompanha o modelo escolhido — trocar de modelo exige migrar a coluna e regerar os vetores.
* **Vetores normalizados:** A ingestão normaliza os embeddings antes de gravar, então distância de cosseno e produto interno produzem a mesma ordenação.
* **Deduplicação por hash do arquivo:** O `sha256` do PDF vai para `metadata`, e não a URL ou o título — o mesmo artigo costuma aparecer com títulos ligeiramente diferentes, mas o arquivo é idêntico.

---

## 4. Ingestão

Os artigos entram no banco por um pipeline **local**, executado na máquina de quem popula a base:

```
PDF → extração de texto → limpeza → sources → articles
    → divisão em chunks → embeddings locais → chunks
```

A limpeza remove cabeçalhos e rodapés repetidos, junta palavras hifenizadas quebradas na virada de linha e descarta a seção de referências bibliográficas, que infla a base sem agregar evidência. PDFs digitalizados (sem camada de texto) passam por OCR.

O script fica fora do repositório compartilhado por depender de credenciais e de um modelo de ~1 GB baixado localmente.
