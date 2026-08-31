# Tipos e Fontes de Dados

> **Referência:** GQ-Data 1 e GQ-Data 3  
> **Responsável:** Beatriz  

---

## 1. Tipos e Formatos de Dados

### 1.1. Dados para o Perfil do Usuário
* **Formato:** Tabular, armazenados no Supabase.
* **Campos/Variáveis:**
  * Sexo
  * Altura
  * Peso
  * Doenças
  * Idade
  * Restrições Alimentares
  * Rotina

---

### 1.2. Dados para Treinamento
* **Formato e Armazenamento:** Extração dos metadados e do conteúdo de cada artigo/post, por meio de OCR e/ou web scraping, armazenados no Supabase.
* **Classificação e Atributos Extraídos:**
  * Tipo do conteúdo (`article`, `post`, `video_transcript`)
  * Fonte (referência à origem)
  * Data (publicação e coleta)
  * Veracidade (`true`, `fake`, `misleading`, `unlabeled`)
  * Conteúdo (texto completo)

---

## 2. Fontes dos Dados

* **Artigos Científicos:** Artigos científicos brasileiros disponibilizados no **Web of Science**, relacionados à nutrição, dietas extremas, transtornos alimentares e dietas voltadas a problemas de saúde.
* **Redes Sociais:** Conteúdos e postagens disponibilizados em redes sociais sobre os temas citados.
