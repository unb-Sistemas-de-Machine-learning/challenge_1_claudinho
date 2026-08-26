# Challenge 1

## 📍 Objetivo
    O primeiro challenge tem como objetivo desenvolver um sistema de Machine Learning capaz de identificar Fake News. O desafio é dividido em **Engage**, **Investigate** and **Act**. Cada parte do desafio é dividido pelas aulas ministradas segundas e quartas, do dia **12/08** até **07/10**

## 🗓️ Schedule
- **12/08:** Big Idea and Essetial Questions
- **17/08:** Challenge Statement
- **19/08:** Guiding Questions
- **24/08:** Fontes e formatos de dados
- **26/08:** Ingestão e preparação de dados + análise exploratória
- **31/08:** Amostragem e rotulagem dos dados do desafio
- **02/09:** Classes desbalanceadas e data augmentation
- **07/09:** Feriado — Independência do Brasil
- **09/09:** Engenharia de features + prevenção de data leakage
- **14/09:** Baselines e seleção de modelos candidatos
- **16/09:** Treinamento, depuração e iteração de modelos
- **21/09:** Métricas e avaliação offline + documentação de experimentos
- **23/09:** Servindo o modelo como API (deploy simples, mitos de deploy)
- **28/09:** Integração da solução + versionamento de código, dados e modelos
- **30/09:** Viés, limitações e IA responsável na solução do grupo
- **05/10:** Demo interna + feedback entre grupos + preparação da entrega
- **07/10:** Apresentação final do Desafio 1 (audiência real)

---

# Guiding Questions

## 📌 Classificações de Prioridade

* **Responder já:** Alto impacto, fácil
* **Planejar:** Alto impacto, difícil
* **Se sobrar tempo:** Baixo impacto, fácil
* **Cortar sem dó:** Baixo impacto, difícil

## 🗄️ Dados

### 1. Qual(is) tipo(s) de dados vamos usar?
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Sexo, Altura, Peso, Doenças, Idade, Restrições Alimentares, Rotina.

### 2. Onde vamos guardar eles? (SQL, JSON)
* **Classificação:** Planejar
* **Responsável:** Beatriz
* **Tarefa:** Utilizaremos SQL pela segurança dos dados.

### 3. Qual a fonte dos dados? (portais, pesquisas, etc.)
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Artigos científicos brasileiros relacionados à nutrição, dietas extremas, transtornos alimentares, e dietas voltadas à problemas de saúde.

## 👤 Usuário

### 1. Quem é o usuário que queremos alcançar?
*Pessoas que querem melhorar a alimentação, e acompanha-la, sem cair no terrorismo nutricional.*
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Criar a "Persona do MVP" (ex: "Estudante universitário que quer se alimentar melhor mas tem pouco tempo").

### 2. Como o usuário pode ter acesso ao nosso programa?
*App*
* **Classificação:** Planejar
* **Responsável:** Beatriz
* **Tarefa:** Aplicativo mobile.

### 3. Por que o usuário buscaria a nossa aplicação?
*Recomendação médica juntamente com necessidade de buscar fontes confiáveis*
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Definir o "Elevator Pitch" da solução em uma frase curta.

## 🤖 Modelo

### 1. Quais métricas de avaliação serão priorizadas para lidar com os riscos de falsos positivos e falsos negativos?
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Definir o limiar aceitável de "Falso Negativo" antes de colocar em produção.

### 2. Qual será a arquitetura e a abordagem de NLP utilizada para garantir respostas baseadas em evidências e evitar "alucinações"?
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Pesquisar e testar uma abordagem RAG (*Retrieval-Augmented Generation*) para garantir base em evidências.

### 3. Como o modelo processará a "linguagem da internet" e diferentes formatos de entrada?
*(Sarcasmo, gírias e links)*
* **Classificação:** [ ]
* **Responsável:**
* **Tarefa:** Treinar o prompt com exemplos de gírias nutricionais comuns.

## 🚀 Produção

### 1. Em qual canal ou plataforma o produto será disponibilizado?
*(WhatsApp, portal/site próprio, rede social, aplicativo dedicado)*
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Definir a plataforma de lançamento do MVP.

### 2. Como será feito o monitoramento e a atualização contínua do modelo em produção?
*(Retraining periódico, monitoramento de drift, versionamento de modelo)*
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Configurar logs básicos de erro nas respostas geradas.

### 3. Quais são os requisitos de escalabilidade e desempenho esperados?
*(Volume de usuários simultâneos, tempo de resposta, custo por requisição)*
* **Classificação:** Se sobrar tempo
* **Responsável:**
* **Tarefa:** Focar em performance apenas após validar o valor do produto para os primeiros usuários.

## ⚖️ Ética

### 1. Como garantir que a aplicação não transforme informações nutricionais potencialmente perigosas ou sem evidência científica em recomendações confiáveis?
*(Verificando fontes científicas e sinalizando informações sem evidência)*
* **Classificação:** Se sobrar tempo
* **Responsável:**
* **Tarefa:** Criar um banco de "testes de estresse" com perguntas que a IA deve negar responder.

### 2. Como proteger diferentes perfis de usuário de recomendações nutricionais inadequadas?
*(Considerando as necessidades individuais e evitando recomendações generalizadas)*
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Implementar filtros de segurança para evitar recomendações para perfis de risco (ex: diagnósticos de transtornos alimentares).

### 3. Como garantir transparência e responsabilidade nas respostas?
*(Informando as limitações da IA e indicando quando é necessário procurar um profissional de saúde)*
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Redigir o "Disclaimer" obrigatório que aparecerá em cada resposta (ex: "Não substitui médico").

# Fontes e formatos de dados
* **Fontes:** Artigos Científicos brasileiros disponibilizados no Web Of Science e conteúdoes disponibilizados em redes sociais.
* **Formatos de dados para treinamento:** Extração dos Metadados e do conteúdo de cada artigo, por meio de OCR e/ou web scrapping, classificando como "tipo do conteúdo", "fonte", "data", "veracidade", "conteúdo", armazenados em Supabase.
* **Formatos de dados para o perfil:** Tabular, armazenados em Supabase.