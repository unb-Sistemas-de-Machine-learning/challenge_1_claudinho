# Proposta de Valor e Elevator Pitch

> **Referência:** GQ-User 3  
> **Responsável:** Matheus Moreira Lopes Perillo 
> **Status:** Respondido  

---

## 1. Elevator Pitch

A resposta da [GQ-User 3](../GQ.md) para *por que o usuário buscaria a nossa aplicação* é **recomendação médica somada à necessidade de buscar fontes confiáveis**. O pitch parte daí: o diferencial que se comunica primeiro é a evidência na tela, não a promessa de saúde.

### 1.1. Versão de 30 segundos

> Todo dia você vê alguém na internet dizendo que um alimento comum faz mal. A gente responde essa dúvida em segundos, em linguagem simples, mostrando o artigo científico brasileiro em que a resposta se apoia. Sem achismo, sem influenciador, com a fonte na tela.

### 1.2. Versão de uma frase

> Checagem de desinformação nutricional em segundos, com o artigo científico na tela.

### 1.3. Por que este ângulo

| Ângulo avaliado | Por que não lidera |
| :--- | :--- |
| **Fim da culpa alimentar** | É o benefício mais forte, mas é consequência. Prometer alívio emocional sem antes estabelecer autoridade soa como o próprio discurso de bem-estar que o produto combate |
| **Acesso a quem não paga consulta** | Verdadeiro e relevante, mas posiciona o produto como substituto barato de nutricionista, exatamente o que ele **não** é (ver a política de recusa em [Ethics/01](../Ethics/01_seguranca_e_anti_alucinacao.md)) |
| **Evidência científica** ✅ | Estabelece autoridade em uma frase, entrega os outros dois benefícios como consequência e descreve com precisão o que o sistema faz: recuperar um trecho de artigo real e responder ancorado nele |

A frase que carrega o produto é **"com a fonte na tela"**. É verificável, é o que nenhum concorrente do quadro da seção 3 entrega, e é exatamente o que a arquitetura RAG da [Model/02](../Model/02_arquitetura_nlp_rag.md) existe para garantir.

---

## 2. Quadro de Proposta de Valor (_Value Proposition Canvas_)

O lado do cliente descreve o Lucas, a persona do MVP definida na [User/01](./01_personas.md).

### 2.1. Do Lado do Usuário (Cliente)

**🎯 Tarefas (_jobs to be done_)**

| Tipo | Tarefa |
| :--- | :--- |
| **Funcional** | Descobrir se uma afirmação sobre alimentação que ele viu na internet é verdade |
| **Funcional** | Decidir, no dia a dia, se muda ou não o que come por causa daquilo |
| **Social** | Não passar por ingênuo no grupo por acreditar em algo que era mito |
| **Social** | Ter argumento com fonte para desmentir alguém próximo |
| **Emocional** | Comer sem medo de estar se prejudicando |
| **Emocional** | Parar de sentir que cuidar da saúde exige dinheiro que ele não tem |

**😖 Dores**

| Dor | Intensidade |
| :--- | :--- |
| Informações que se contradizem, sem forma de arbitrar entre elas | 🔴 Alta |
| Culpa ao comer alimentos comuns e acessíveis como arroz, feijão e pão | 🔴 Alta |
| Consulta com nutricionista fora do orçamento | 🔴 Alta |
| Artigo científico é inacessível: paywall, inglês e jargão | 🟠 Média |
| Medo de já ter feito mal a si mesmo seguindo algum conselho da internet | 🟠 Média |
| Tempo escasso: nenhuma checagem que exija mais que alguns minutos vai acontecer | 🟠 Média |

**😄 Ganhos esperados**

* Resposta clara e rápida, em português e sem jargão.
* Tranquilidade para manter a alimentação que ele já pode pagar.
* Sensação de estar no controle, e não à mercê do próximo vídeo do feed.
* Algo que ele possa mostrar a outra pessoa como prova.

### 2.2. Do Lado da Nossa Solução (Produto)

**📦 Produtos e serviços**

* App mobile com checagem por texto, link ou print ([User/02](./02_acesso_e_canais.md)).
* Card de resposta com veredito, faixa de risco e explicação em linguagem simples.
* Seção expansível de fontes com título, autores, periódico, DOI e o trecho exato utilizado.
* Perfil de saúde opcional que condiciona a resposta à condição de quem pergunta.
* Botão de 👍 / 👎 que alimenta a melhoria contínua ([Production/02](../Production/02_monitoramento_e_mlops.md)).

**💊 Analgésicos (aliviadores de dor)**

| Dor atacada | Como o produto alivia |
| :--- | :--- |
| Informações contraditórias | Veredito único ancorado em literatura científica brasileira, com limiares de risco calibrados ([Model/01](../Model/01_metricas_e_avaliacao.md)) |
| Culpa alimentar | Guardrails que proíbem tom julgador, e `tom_julgador` existe como motivo de feedback negativo no contrato |
| Custo da consulta | Checagem gratuita no MVP, sem substituir o profissional: toda resposta encaminha quando o caso pede |
| Artigo inacessível | O RAG lê o artigo e devolve o trecho relevante traduzido em linguagem comum |
| Falta de tempo | Colar um link e receber o card, sem cadastro clínico obrigatório antes da primeira resposta |

**🎁 Criadores de ganho**

| Ganho | Como o produto cria |
| :--- | :--- |
| Confiança verificável | DOI e trecho citado na tela, e não apenas a afirmação de que a fonte existe |
| Argumento compartilhável | O card de fontes é pensado para ir para o grupo da família, como na persona Marcos |
| Segurança para grupos de risco | Filtros por condição clínica e recusa segura ([Ethics/02](../Ethics/02_grupos_de_risco_e_filtros.md)) |
| Sensação de controle | O usuário decide o que fazer com a informação; o produto informa, não prescreve |

### 2.3. Encaixe entre os dois lados

| Dor ou tarefa do usuário | Elemento da solução | Onde está especificado |
| :--- | :--- | :--- |
| Arbitrar entre informações contraditórias | Veredito com `risk_score` e faixa calibrada | [Production/01](../Production/01_plataforma_e_deploy.md), seção 2.1 |
| Confiar na resposta | Card de fontes com DOI e trecho | [Ethics/03](../Ethics/03_transparencia_e_disclaimers.md), seção 3 |
| Checar sem sair do fluxo do feed | Entrada por link e por print | [User/02](./02_acesso_e_canais.md), seção 2 |
| Não receber conselho perigoso | Guardrails e recusa segura | [Ethics/01](../Ethics/01_seguranca_e_anti_alucinacao.md) |
| Resposta que considere a condição dele | Perfil de saúde opcional e `use_profile` | [Production/01](../Production/01_plataforma_e_deploy.md), seção 2.3 |
| Resposta rápida | Cache semântico e SLA de latência | [Production/03](../Production/03_escalabilidade_e_desempenho.md) |

> **Lacuna assumida:** a tarefa emocional *"parar de sentir que cuidar da saúde exige dinheiro"* é atendida só em parte. O produto reduz o custo de verificar informação, mas não resolve o custo de acompanhamento nutricional continuado. É honesto dizer isso na apresentação, em vez de prometer o que o MVP não entrega.

---

## 3. Matriz Comparativa de Diferenciais

| Recurso | Redes Sociais / Google | ChatGPT / LLMs Genéricos | Nutricionista particular | Nossa Solução |
| :--- | :--- | :--- | :--- | :--- |
| **Base em Evidências Brasileiras** | ❌ Quase nula (algoritmo prioriza engajamento) | ⚠️ Genérica e desatualizada | ✅ Alta | ✅ RAG focado em ciência e diretrizes brasileiras |
| **Combate ao Terrorismo Nutricional** | ❌ Costuma incentivar o pânico | ⚠️ Neutro, pode alucinar ou validar mitos | ✅ Depende do profissional | ✅ Guardrails explícitos pró-alimentação saudável |
| **Citação de Artigos e DOIs** | ❌ Raro | ⚠️ Frequentes alucinações de links/autores | ⚠️ Raramente por escrito | ✅ Recuperação exata de fragmentos da base |
| **Custo para o usuário** | ✅ Gratuito | ⚠️ Gratuito com limite, ou assinatura | ❌ Algumas centenas de reais por consulta | ✅ Gratuito no MVP |
| **Tempo até a resposta** | ⚠️ Minutos garimpando resultados | ✅ Segundos | ❌ Dias ou meses de espera | ✅ Segundos ([Production/03](../Production/03_escalabilidade_e_desempenho.md)) |
| **Checagem a partir de print ou link** | ❌ Não se aplica | ⚠️ Parcial e sem tratamento dedicado | ❌ Não se aplica | ✅ `input_type` aceita `url` e `image` |
| **Adaptação ao perfil de saúde** | ❌ Inexistente | ⚠️ Só se o usuário descrever a cada conversa | ✅ Total | ✅ Perfil persistido que aciona filtros de risco |
| **Proteção a grupos vulneráveis** | ❌ Nenhuma | ⚠️ Inconsistente | ✅ Total | ✅ Filtros e recusa segura ([Ethics/02](../Ethics/02_grupos_de_risco_e_filtros.md)) |
| **Encaminhamento a profissional** | ❌ Nenhum | ⚠️ Ocasional | ✅ É o profissional | ✅ Disclaimer obrigatório em toda resposta |
| **Profundidade e acompanhamento** | ❌ Nenhum | ⚠️ Superficial | ✅ **Vantagem do profissional** | ❌ Fora do escopo |

### 3.1. Onde nós perdemos, e por que tudo bem

A última linha é intencional. O produto **não** compete com o nutricionista, ele ocupa o espaço entre o Google e a consulta: checagem pontual de alegações, não acompanhamento. Assumir isso é o que sustenta a coerência com o disclaimer obrigatório da [Ethics/03](../Ethics/03_transparencia_e_disclaimers.md). Um produto que se vendesse como substituto de profissional teria que escolher entre o próprio pitch e o próprio guardrail.

O concorrente real é o **status quo**: não checar nada e seguir no achismo, que é o desfecho descrito na última linha do mapa de empatia da [User/01](./01_personas.md).

---

## 4. Próximos Passos

- [ ] Testar as duas versões do pitch nas entrevistas de validação de personas e ficar com a que for repetida de volta com mais fidelidade.
- [ ] Confirmar se a gratuidade se sustenta fora do MVP, cruzando com a estimativa de custo por requisição da [Production/03](../Production/03_escalabilidade_e_desempenho.md).
- [ ] Fechar com a frente de Ética a redação exata do encaminhamento a profissional, já que ela aparece no pitch como diferencial.
