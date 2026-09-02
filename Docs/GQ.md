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
* **Responsável:** Beatriz
* **Tarefa:** Sexo, Altura, Peso, Doenças, Idade, Restrições Alimentares, Rotina.

### 2. Onde vamos guardar eles? (SQL, JSON)
* **Classificação:** Planejar
* **Responsável:** Beatriz
* **Tarefa:** Utilizaremos SQL pela segurança dos dados.

### 3. Qual a fonte dos dados? (portais, pesquisas, etc.)
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Artigos científicos brasileiros relacionados à nutrição, dietas extremas, transtornos alimentares, e dietas voltadas a problemas de saúde.

---

## 👤 Usuário

### 1. Quem é o usuário que queremos alcançar?
*Pessoas que querem melhorar a alimentação, e acompanhá-la, sem cair no terrorismo nutricional.*
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Criar a "Persona do MVP" (ex: "Estudante universitário que quer se alimentar melhor mas tem pouco tempo").

### 2. Como o usuário pode ter acesso ao nosso programa?
*App*
* **Classificação:** Planejar
* **Responsável:** Beatriz
* **Tarefa:** Aplicativo mobile.

### 3. Por que o usuário buscaria a nossa aplicação?
*Recomendação médica junto à necessidade de buscar fontes confiáveis*
* **Classificação:** Responder já
* **Responsável:** Beatriz
* **Tarefa:** Definir o "Elevator Pitch" da solução numa frase curta.

---

## 🤖 Modelo

### 1. Quais métricas de avaliação serão priorizadas para lidar com os riscos de falsos positivos e falsos negativos?
* **Classificação:** Planejar
* **Responsável:** Ana
* **Tarefa:** Definir o limiar aceitável de "Falso Negativo" antes de colocar em produção.

### 2. Qual será a arquitetura e a abordagem de NLP utilizada para garantir respostas baseadas em evidências e evitar "alucinações"?
* **Classificação:** Planejar
* **Responsável:** Ana
* **Tarefa:** Pesquisar e testar uma abordagem RAG (*Retrieval-Augmented Generation*) para garantir base em evidências.

### 3. Como o modelo processará a "linguagem da internet" e diferentes formatos de entrada?
*(Sarcasmo, gírias e links)*
* **Classificação:** Planejar
* **Responsável:** Ana
* **Tarefa:** Treinar o prompt com exemplos de gírias nutricionais comuns.

---

## 🚀 Produção

### 1. Em qual canal ou plataforma o produto será disponibilizado?
*(WhatsApp, portal/site próprio, rede social, aplicativo dedicado)*
* **Classificação:** Responder já
* **Responsável:** João
* **Tarefa:** Definir a plataforma de lançamento do MVP.

### 2. Como será feito o monitoramento e a atualização contínua do modelo em produção?
*(Retraining periódico, monitoramento de drift, versionamento de modelo)*
* **Classificação:** Planejar
* **Responsável:** João
* **Tarefa:** Configurar logs básicos de erro nas respostas geradas.

### 3. Quais são os requisitos de escalabilidade e desempenho esperados?
*(Volume de usuários simultâneos, tempo de resposta, custo por requisição)*
* **Classificação:** Se sobrar tempo
* **Responsável:** João
* **Tarefa:** Focar em desempenho apenas após validar o valor do produto para os primeiros usuários.

---

## ⚖️ Ética

### 1. Como garantir que a aplicação não transforme informações nutricionais potencialmente perigosas ou sem evidência científica em recomendações confiáveis?
*(Verificando fontes científicas e sinalizando informações sem evidência)*
* **Classificação:** Se sobrar tempo
* **Responsável:** Maria Clara
* **Tarefa:** Criar um banco de "testes de estresse" com perguntas que a IA deve identificar e recursar-se a responder, garantindo que apenas informações baseadas em ciência sejam validadas.

### 2. Como proteger diferentes perfis de usuário de recomendações nutricionais inadequadas?
*(Considerando as necessidades individuais e evitando recomendações generalizadas)*
* **Classificação:** Planejar
* **Responsável:** Maria Clara
* **Tarefa:** Desenvolver filtros de segurança que impeçam a IA de emitir recomendações para grupos de risco, como pessoas com diagnósticos de transtornos alimentares, gestantes ou indivíduos com condições de saúde específicas.

### 3. Como garantir transparência e responsabilidade nas respostas?
*(Informando as limitações da IA e indicando quando é necessário procurar um profissional de saúde)*
* **Classificação:** Responder já
* **Responsável:** Maria Clara
* **Tarefa:** Redigir um "Disclaimer" padrão, obrigatório em todas as respostas, com frases como: "Esta informação não substitui a consulta com um nutricionista ou médico. Sempre procure orientação profissional para decisões sobre sua saúde."