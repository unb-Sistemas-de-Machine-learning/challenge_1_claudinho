# Spec: Guardrails éticos, grupos de risco e avisos

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema
Quem pergunta sobre nutrição na internet às vezes descreve uma conduta perigosa (jejum de vários dias, laxante para emagrecer, troca de remédio por dieta). Responder "mito" ou "verdade" a essas perguntas, como se fossem alegações comuns, pode causar dano. Também há públicos que a ferramenta não deve atender (menores de 18 anos, pela LGPD) ou que precisam de um aviso a mais (gestantes, pessoas com condição crônica).

## Objetivo
Barrar antes de qualquer busca ou LLM as condutas de risco crítico e o público menor de idade, responder com cuidado e canais de apoio, e acrescentar a toda resposta de checagem os avisos que a situação exige, com texto homologado pela frente de Ética.

## Escopo
### Dentro
- Recusa segura para condutas de risco crítico, com veredito `recusa_segura` (APP/model/claim_extractor.py, `PADROES_RISCO_CRITICO` e `checar_recusa_segura`).
- Recusa de serviço para menor de 18 anos, no texto da pergunta (pipeline) e na data de nascimento do perfil (403 `age_restricted`).
- Tela `/menor-de-idade` no front (web/src/telas/Bloqueado.tsx).
- Disclaimer curto em toda resposta, mais aviso de evidência limitada, de gestantes e lactantes e de condição clínica (APP/model/disclaimers.py).
- Avisos também a partir das condições do perfil de saúde, não só do texto da pergunta.
- Reformulação amigável da pergunta e padrões semânticos de classificação (APP/model/claim_extractor.py e APP/model/classifier.py).
- Flag `safe_refusal` em `/extract-claim`, para a tela não prometer "procurando nos estudos" quando a checagem vai virar resposta de cuidado.

### Fora (e por quê)
- Moderação por LLM: o guardrail é por expressão regular, determinístico e sem custo, e roda antes do LLM.
- Verificação real de idade: só há declaração no texto e data de nascimento no perfil, sem documento.
- Campo próprio na API para a abertura do guardrail: decisão em aberto (ver Riscos).
- Revisão clínica dos padrões por profissional de saúde: não consta no repositório.

## Requisitos funcionais
- RF-01: pergunta que casa com `PADROES_RISCO_CRITICO` devolve `verdict = "recusa_segura"`, `risk_level = "alto"`, sem fontes e sem chamar busca nem LLM.
- RF-02: a resposta de cuidado traz abertura específica, a pergunta reformulada, justificativa e orientação com canais de apoio.
- RF-03: os padrões cobrem jejum extremo, substância tóxica, método compensatório, troca de medicamento, gestação e lactentes, e substâncias sem prescrição.
- RF-04: texto em primeira pessoa declarando menos de 18 anos ("tenho 15 anos", "sou menor de idade") recebe recusa de serviço antes dos demais guardrails.
- RF-05: "meu filho tem 15 anos" e "tenho 15 anos de diabetes" não são tratados como menor de idade.
- RF-06: `PUT` do perfil com data de nascimento de menor de 18 anos responde 403 com código `age_restricted`.
- RF-07: toda resposta de checagem leva o disclaimer curto como primeiro bloco.
- RF-08: veredito `cautela` acrescenta o aviso de evidência limitada.
- RF-09: menção a gestação ou amamentação acrescenta o aviso de gestantes e lactantes; menção a condição crônica acrescenta o de condições clínicas; com os dois, só o de gestantes aparece.
- RF-10: as condições do perfil de saúde entram no cálculo dos avisos, como se a pessoa as tivesse escrito.
- RF-11: perfil com condições marca a geração como dado sensível (o roteamento de provedor está na spec 01).
- RF-12: o log registra `safe_refusal` e `restricao_de_idade` sem gravar o texto da pergunta.
- RF-13: o front mostra a tela `/menor-de-idade` e oferece o caminho a partir das boas-vindas e do formulário de perfil.

## Requisitos não funcionais
- RNF-01 (segurança): os guardrails rodam antes de busca e LLM, então não dependem da disponibilidade de provedor externo.
- RNF-02 (privacidade): o log guarda comprimento e flags, nunca o texto; condição de saúde do perfil não vai a provedor externo.
- RNF-03 (conformidade): os textos dos avisos são cópia literal de Docs/Ethics/03 e Docs/Ethics/02, conferidos por teste.
- RNF-04 (manutenção): os padrões ficam em listas de regex com abertura, justificativa e orientação ao lado, para revisão por quem não programa.

## Critérios de aceite
- [x] Condutas de risco são barradas (tests/test_guardrails.py, `test_barra_as_condutas_de_risco`).
- [x] Dúvidas legítimas não são barradas (`test_nao_barra_duvidas_legitimas`).
- [x] Resposta de cuidado segue a estrutura homologada (`test_resposta_de_cuidado_segue_a_estrutura_homologada`).
- [x] Textos dos avisos batem com o documento de Ética (tests/test_disclaimers.py, `test_texto_e_copia_literal_do_documento_de_etica`).
- [x] Gestante, condição crônica e `cautela` recebem o aviso certo, sem repetir (tests/test_disclaimers.py).
- [x] Menor de idade recebe recusa sem busca nem LLM (`test_menor_de_idade_recebe_recusa_sem_busca_nem_llm`).
- [x] Perfil de menor é recusado e quem acabou de fazer 18 é aceito (`test_perfil_de_menor_de_idade_e_recusado`, `test_perfil_de_quem_acabou_de_fazer_18_e_aceito`).
- [x] Condição do perfil gera aviso sem a pessoa escrever (tests/test_perfil_na_checagem.py).
- [x] Classificação semântica e padrões amigáveis testados (tests/test_classifier.py, tests/test_claim_extractor.py).
- [ ] A abertura específica de cada guardrail chega ao usuário como campo da API.
- [ ] Revisão dos padrões por nutricionista ou psicólogo.

## Decisões
| Decisão | Por quê | Onde |
|---|---|---|
| Menor de idade é checado antes dos guardrails de risco | Não há serviço a oferecer a menor, nem a resposta de cuidado | APP/model/pipeline.py |
| Idade só vale em primeira pessoa | Quem pergunta pelo filho é adulto; "15 anos de diabetes" é duração | APP/model/disclaimers.py |
| Resposta de cuidado como resposta normal (200) com veredito `recusa_segura` | O front trata como resultado, com tom de acolhimento, não como erro | APP/model/pipeline.py, web/src/lib/vereditos.ts |
| Menor no perfil devolve 403 `age_restricted` | O contrato distingue bloqueio de idade de erro de validação | APP/routers/profile.py |
| Texto dos avisos copiado literalmente da Ética | Evitar divergência entre documento e produto | APP/model/disclaimers.py, tests/test_disclaimers.py |
| Avisos usam texto da pergunta mais condições do perfil | Quem tem o dado no perfil não precisa repetir | APP/model/pipeline.py |
| `/extract-claim` devolve `safe_refusal` | A tela de carregamento não promete busca em estudos | APP/routers/extract_claim.py |

## Riscos e limitações conhecidas
- Revisão do PR #47: a abertura específica do guardrail some do texto exibido. O pipeline descarta o primeiro bloco da resposta de cuidado e o front mostra uma frase genérica por veredito. Decisão em aberto: a API devolver a abertura como campo próprio.
- Regex tem falso negativo (reformulações não previstas) e pode ter falso positivo. Sem revisão clínica, a cobertura é a lista atual.
- A idade é autodeclarada, então é contornável.
- O aviso de gestante e o de condição crônica usam listas fixas de termos; condição fora da lista não gera aviso.
- Existem cópias "nome 2" de arquivos na pasta sincronizada (web/src/lib 2, por exemplo); não fazem parte do código.

## Referências
- [Ética 01: segurança e anti-alucinação](../../Ethics/01_seguranca_e_anti_alucinacao.md)
- [Ética 02: grupos de risco e filtros](../../Ethics/02_grupos_de_risco_e_filtros.md)
- [Ética 03: transparência e disclaimers](../../Ethics/03_transparencia_e_disclaimers.md)
- [Personas](../../User/01_personas.md)
- [Spec 01: checagem com RAG](../01-checagem-rag/spec.md)
- Issues: #7 (Guardrails), #8 (Regras amigáveis), #10 (Padrões semânticos), #30 (boas-vindas, termos e bloqueio de menor), #25 (perfil na checagem e aviso na resposta), #19 (formulário do perfil e consentimento LGPD)
- PRs: #42 (reformulação amigável), #43 (guardrails para cenários críticos), #44 (padrões semânticos), #47 (formulário de perfil), #6 (autenticação, rate limiting e perfil de saúde)
