# Guiding Questions

## 📌 Classificações de Prioridade

* **Responder já:** Alto impacto, fácil
* **Planejar:** Alto impacto, difícil
* **Se sobrar tempo:** Baixo impacto, fácil
* **Cortar sem dó:** Baixo impacto, difícil

---

## 🗄️ Dados

### 1. Qual(is) tipo(s) de dados vamos usar?
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Listar os campos essenciais (ex: idade, peso, tabelas nutricionais, alimentos) necessários para o MVP.

### 2. Onde vamos guardar eles? (SQL, JSON)
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Optar pela solução mais rápida e simples (ex: JSON local ou Firebase) para evitar burocracia técnica.

### 3. Qual a fonte dos dados? (portais, pesquisas, etc.)
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Mapear 3 fontes de dados governamentais ou acadêmicas confiáveis (ex: tabelas TACO).

---

## 👤 Usuário

### 1. Quem é o usuário que queremos alcançar?
*(Comunidade de nutrição, pessoas com TA, pessoas que se preocupam com a saúde)*
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Criar a "Persona do MVP" (ex: "Estudante universitário que quer se alimentar melhor mas tem pouco tempo").

### 2. Como o usuário pode ter acesso ao nosso programa?
*(App, extensão web)*
* **Classificação:** Planejar
* **Responsável:**
* **Tarefa:** Comparar esforço de desenvolvimento (extensão vs. site) e escolher o canal de menor fricção para o usuário.

### 3. Por que o usuário buscaria a nossa aplicação?
*(Recomendação médica, necessidade de buscar fontes confiáveis)*
* **Classificação:** Responder já
* **Responsável:**
* **Tarefa:** Definir o "Elevator Pitch" da solução em uma frase curta.

---

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

---

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

---

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