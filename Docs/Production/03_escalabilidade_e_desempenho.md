# Escalabilidade, Desempenho e Custos

> **Referência:** GQ-Production 3  
> **Responsável:** João Pedro Araújo de Freitas Lyra  
> **Status:** Em desenvolvimento  

---

## 1. Requisitos de Desempenho (SLAs)

Para garantir que o usuário não abandone o app durante a consulta de uma informação vista na rede social:

| Métrica de Desempenho | Meta MVP |
| :--- | :--- |
| **Tempo até o Primeiro Token (TTFT)** |  |
| **Latência Total da Resposta** |  |
| **Tempo de Busca no pgvector (HNSW)** |  |
| **Disponibilidade (Uptime)** |  |
| **Capacidade Simultânea** |  |

---

## 2. Estratégias de Otimização de Custo e Velocidade

### 2.1. Cache Semântico (*Semantic Caching*)
Muitos usuários farão variações da mesma pergunta popular (ex: *"Água com limão emagrece?"* vs *"Tomar água e limão de manhã queima gordura?"*).


### 2.2. Rate Limiting e Proteção contra Abusos
* Implementar limite de **requisições por minuto por IP/usuário** para prevenir _scraping_ abusivo e estouro de cota da API do modelo.

### 2.3. Estimativa de Custos para o MVP
* **Embeddings:** 
* **LLM:**
* **Hospedagem Supabase + Backend:** Camada gratuita (*Free Tier*).
* **Custo Total Estimado do MVP:** 

---
