# Claudinho · Checagem de Desinformação Nutricional

Bem-vindo à documentação oficial do **Claudinho**, uma solução desenvolvida no âmbito do desafio de *Sistemas de Machine Learning* (UnB - 2026).

O projeto consiste em um sistema inteligente (API e PWA) para identificação e combate à desinformação nutricional e ao terrorismo alimentar disseminados na internet e redes sociais, provendo respostas cientificamente embasadas, empáticas e acessíveis.

---

## Pilares do Sistema

- **Ancoragem Científica Estrita (*Strict Grounding*):** Nenhuma resposta científica é gerada sem suporte explícito em artigos científicos ou tabelas nutricionais (como a TBCA/USP e SciELO).
- **Protocolo Anti-Alucinação:** Quando a base científica não dispõe de evidências suficientes sobre a alegação, o modelo assume a ausência de estudos (*Veredito: sem evidência*) em vez de especular ou inventar fontes.
- **Guardrails de Segurança e Recusa Segura:** Alegações ligadas a comportamentos de risco extremo, transtornos do comportamento alimentar (TCA) ou grupos vulneráveis (ex.: gestantes e lactantes) acionam recusa imediata, acolhedora e orientada a canais de apoio (CVV 188, UBS, CRN).
- **Comunicação Empática (Persona Lucas):** Linguagem acessível, compreensiva e sem culpabilização ("alívio primeiro: *pode respirar, isso é mito*").

---

## Mapa da Documentação

Navegue pelos módulos do projeto através do menu superior e lateral:

| Seção | Descrição | Principais Tópicos |
| :--- | :--- | :--- |
| [**Guiding Questions**](./GQ.md) | Questões-guia que direcionam o desafio. | Priorização, objetivos e responsáveis de cada frente. |
| [**Guia da IA**](./GUIA_DA_IA.md) | Arquitetura técnica e pipeline da inteligência artificial. | Fluxograma do pipeline, RAG, classificação de risco e fallback. |
| [**Modelo (ML & RAG)**](./Model/README.md) | Detalhes de modelagem e Processamento de Linguagem Natural. | Métricas ($F_2$, Recall, Ragas), vetorização semântica, gírias da internet. |
| [**Ética & Segurança**](./Ethics/README.md) | Mitigação de danos e IA responsável. | Red teaming, filtros para grupos de risco (TCA), disclaimers e DOIs. |
| [**Produção & MLOps**](./Production/README.md) | Engenharia de software e deploy. | Endpoints REST da API, monitoramento de drift, caching semântico e latência. |
| [**Dados**](./Data/README.md) | Fontes de conhecimento e modelagem. | Bases científicas (SciELO, Web of Science), PostgreSQL/Supabase e `pgvector`. |
| [**Usuário & Produto**](./User/README.md) | Pesquisa de produto e proposta de valor. | Personas (Lucas, Camila, Renata), canais de acesso e *Value Proposition Canvas*. |
| [**Design System**](./Design/design-system.md) | Identidade visual, tokens e interface. | Cores, tipografia (Atkinson Hyperlegible, Bricolage), acessibilidade e protótipo. |

---

## Equipe de Desenvolvimento

| Integrante | Matrícula | GitHub | Frente Principal |
| :--- | :--- | :--- | :--- |
| **Ana Luiza Hoffmann Ferreira** | 202015901 | [@AnHoff](https://github.com/AnHoff) | Modelo (ML & RAG) |
| **Beatriz Brandão Fidelis Batista** | 242005202 | [@beatrizbranfb](https://github.com/beatrizbranfb) | Dados & Usuário |
| **João Pedro Araújo de Freitas Lyra** | 232003661 | [@jadequilin](https://github.com/jadequilin) | Produção & MLOps |
| **Matheus Moreira Lopes Perillo** | 190093421 | [@matheusperillo03](https://github.com/matheusperillo03) | Infraestrutura & Integração |
| **Maria Clara de Freitas Pina** | 232021900 | [@mariapinaclara](https://github.com/mariapinaclara) | Ética & Segurança |

*ATENÇÃO! Todos os membros apresentaram contribuições em frentes variadas e participaram ativamente do projeto.*

---

## Repositório e Código

- **Repositório GitHub:** [unb-Sistemas-de-Machine-learning/challenge_1_claudinho](https://github.com/unb-Sistemas-de-Machine-learning/challenge_1_claudinho)
- **API Backend:** Desenvolvida em Python com FastAPI, Pydantic e Supabase (`APP/`).
- **Frontend PWA:** Desenvolvido com React/Vite, TypeScript e Tailwind (`web/`).
