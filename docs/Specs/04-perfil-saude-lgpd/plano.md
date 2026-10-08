# Plano de implementação: Perfil de saúde, consentimento e LGPD

> Plano reconstruído em 07/10/2026 a partir do histórico do repositório. As etapas abaixo são as que de fato aconteceram, na ordem em que entraram.

## Visão da arquitetura
```mermaid
flowchart LR
  F[PerfilEdicao.tsx] -->|PUT /profile| R[routers/profile.py]
  F --> L[(aparelho)]
  R --> P[repositorios/perfil.py]
  P --> S[(Supabase, RLS)]
  C[/check-claim] -->|use_profile| P
  C --> G[pipeline: avisos e dado sensível]
  G --> M[só modelo próprio]
```
O formulário valida local, grava na API e no aparelho. A API guarda por um repositório (memória ou Supabase, escolhido por `REPOSITORIOS`). O `/check-claim` busca o perfil quando `use_profile` vem ligado, usa as condições para os avisos e, havendo condição, restringe a geração ao modelo próprio.

## Componentes e arquivos
| Arquivo | Papel |
|---|---|
| `web/src/telas/PerfilEdicao.tsx` | Formulário de 5 seções, consentimento, bloqueio de menor |
| `web/src/telas/Perfil.tsx` | Resumo e aviso "Perfil salvo" |
| `APP/schemas.py` | Modelo `Profile` e validações (limites, data futura, consentimento) |
| `APP/routers/profile.py` | GET, PUT e DELETE do perfil, bloqueio de menor, log só com booleanos |
| `APP/repositorios/perfil.py` | Repositórios em memória e Supabase |
| `deploy/sql/001_profiles_e_feedback.sql` | Tabela, RLS e função de expurgo |
| `APP/routers/check_claim.py` | Carrega o perfil com `use_profile`, tolera falha |
| `APP/model/pipeline.py` | Avisos pelo perfil e marca de dado sensível |
| `Docs/Ethics/02_grupos_de_risco_e_filtros.md` | Política de grupos de risco e prazo de expurgo |

## Etapas
1. API de perfil, autenticação e rate limit: PR #6 (issue #37).
2. Formulário de perfil com consentimento da LGPD: issue #19, PR #47 (Ana). Na revisão entraram validação local de altura e peso, recusa de data futura e mensagens próprias.
3. Perfil na checagem: avisos sem constar na pergunta, geração sensível e log sem conteúdo: issue #25, entregue no PR #51 (o #48, que propôs isso primeiro, foi fechado e o conteúdo seguiu pelo #51).
4. Persistência e exclusão: PR #51 (repositório Supabase, RLS, `DELETE /api/v1/profile`, expurgo).
5. Prazo de expurgo de dado sensível (6 meses) documentado: PR #52.
6. Resumo do perfil no front: issue #34.

## Testes
- Front: `web/src/telas/PerfilEdicao.test.tsx` e `web/src/telas/Perfil.test.tsx`.
- API: `tests/test_profile.py`, `tests/test_exclusao_de_perfil.py`, `tests/test_perfil_na_checagem.py`, `tests/test_repositorio_perfil_supabase.py`.
- Não rodados na escrita deste plano (a pasta sincronizada trava o pytest).

## Estado atual
| Item | Situação |
|---|---|
| Formulário com 5 seções e consentimento | ✅ |
| Bloqueio de menor de 18 (front e API) | ✅ |
| PUT, GET e DELETE do perfil | ✅ |
| Perfil na checagem e geração sensível | ✅ |
| Logs sem dado clínico | ✅ |
| RLS e função de expurgo no SQL | ✅ |
| Expurgo agendado em produção (pg_cron) | 🟡 |
| Apagar perfil pelo app | ⬜ |
| Revogar consentimento direto (Art. 8º, §5º) | ⬜ |
| Perfil lido da API com conta (issue #22) | 🟡 |
| Toque acidental na data no iOS | ⬜ |

## Próximos passos
- Botão único para revogar o consentimento, que limpa as condições.
- Ligar o botão de apagar perfil ao `DELETE /api/v1/profile`.
- Ativar o pg_cron e confirmar o expurgo em produção.
- Corrigir o campo de data no iOS (tipo de entrada ou confirmação antes de bloquear).
- Ler o perfil da API quando houver conta e conciliar com o do aparelho.
