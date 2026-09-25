# Proteção de Grupos Vulneráveis e Filtros de Risco

> **Referência:** GQ-Ethics 2  
> **Responsável:** Maria Clara de Freitas Pina  
> **Status:** Em desenvolvimento  

---

## 1. Mapeamento de Públicos Vulneráveis

Recomendações nutricionais genéricas que funcionam razoavelmente bem para adultos saudáveis podem ser severamente danosas para grupos com demandas fisiológicas ou psicológicas particulares:

```mermaid
mindmap
  root((Grupos Vulneráveis))
    Transtornos Alimentares
      Anorexia Nervosa
      Bulimia Nervosa
      Compulsão Alimentar
      Ortorexia
    Ciclos de Vida Especiais
      Gestantes
      Lactantes
      Idosos
    Condições Clínicas Crônicas
      Diabetes Mellitus Tipo 1 e 2
      Insuficiência Renal Crônica
      Hipertensão Severa
      Doença Celíaca
```

> **Restrição Legislação / Escopo (LGPD Art. 14):** O público menor de 18 anos encontra-se **fora do escopo comercial e de uso do aplicativo** devido às exigências de consentimento dos responsáveis para tratamento de dados sensíveis de saúde. Caso o sistema identifique uso por menor via perfil ou prompt, será acionado um bloqueio preventivo de segurança.

---

## 2. Filtros de Segurança por Grupo

Os filtros atuam na camada de entrada e processamento do prompt, aplicando regras específicas para cada púbico mapeado:

* **Transtornos Alimentares (TCA):** Bloqueio imediato de termos e métricas associados a comportamento purgativo, contagem obsessiva de calorias extremas ou apologia à magreza excessiva. O filtro interrompe a checagem padrão e ativa a resposta acolhedora de apoio via análise semântica no prompt.
* **Condições Clínicas Crônicas:** Detecção de restrições nutricionais severas sem acompanhamento (ex: corte total de carboidratos para diabéticos Tipo 1 ou restrição de sódio/potássio sem orientação para doentes renais). O filtro adiciona alertas explícitos de risco fisiológico.
* **Ciclos de Vida Especiais (Gestantes, Lactantes e Idosos):** Identificação de perfis ou restrições alimentares aplicadas a esses grupos, exigindo que a IA ressalte a necessidade de acompanhamento médico e nutricional individualizado.
* **Menores de 18 anos (Fora do Escopo / Proteção Ativa):** Identificação de perfil com idade inferior a 18 anos ou menção explícita no prompt. Aciona recusa imediata de serviço por restrição da LGPD (Art. 14 - consentimento de dados de saúde), orientando o encerramento do uso.

---

## 3. Matriz de Decisão dos Filtros de Proteção

| Grupo / Condição | Gatilho de Entrada (*Prompt*) | Ação do Filtro | Tipo de Resposta |
| :--- | :--- | :--- | :--- |
|**Menores de 18 anos** | Cadastro/Perfil com idade < 18 ou menção explícita em prompt ("tenho 15 anos"). | **Bloqueio de Uso / Recusa de Serviço** | "O uso deste aplicativo é restrito a maiores de 18 anos (LGPD Art. 14). Recomendamos consultar um nutricionista com seu responsável legal." |
| **Transtornos Alimentares (Anorexia/Bulimia/Ortorexia)** | Menção a jejuns prolongados, uso de laxantes para emagrecer ou purgação. | **Interrupção de Checagem / Redirecionamento** | Recusa segura e acolhedora + Indicação de canais de apoio. |
|**Gestantes e Lactantes** | Menção explícita no prompt (ex: "estou grávida e quero fazer cetogênica") OU Perfil ativo. | **Alerta de Segurança + Filtro de Restrição** | Aviso sobre riscos de deficiência nutricional fetal/materna + Orientações para acompanhamento pré-natal. |
| **Doenças Crônicas (Diabetes, Insuficiência Renal, Celíacos)** | Dúvidas sobre exclusão radical de macronutrientes ou consumo de alimentos com potencial contaminação. | **Injeção de Contexto de Risco Clínico** | Resposta baseada em evidências + Disclaimer obrigatório sobre a complexidade da condição. |
| **População Geral (Alegações Populares sem Risco Imediato)** | Perguntas sobre mitos comuns (ex: "Água com limão em jejum emagrece?"). | **Fluxo Padrão de Checagem** | Avaliação científica normal + Citação de fontes com DOI + Disclaimer curto no rodapé. |

---
