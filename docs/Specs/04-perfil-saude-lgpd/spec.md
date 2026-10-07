# Spec: Perfil de saúde, consentimento e LGPD

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema
O Claudinho responde melhor quando conhece a pessoa (gestante, condição crônica, restrição alimentar). Mas condição clínica é dado pessoal sensível (LGPD Art. 5º, II), e menor de 18 anos não pode ter dado tratado sem as garantias do Art. 14. Sem um perfil, os avisos de grupo de risco dependem de a pessoa escrever "estou grávida" na pergunta. Com um perfil mal feito, o app coleta demais ou vaza dado clínico para log e provedor externo.

## Objetivo
Permitir um perfil opcional, com consentimento explícito quando houver condição clínica, que melhora os avisos da checagem sem expor o conteúdo em log, sem enviá-lo a provedor externo e com saída fácil (apagar, expurgar).

## Escopo
### Dentro
- Formulário de perfil com 5 seções, todas opcionais (issue #19, PR #47).
- Consentimento explícito obrigatório quando há condição clínica.
- Bloqueio de menor de 18 anos, no front e na API.
- Endpoints GET, PUT e DELETE de `/api/v1/profile`, com persistência em memória ou Supabase.
- Uso do perfil no `/check-claim` (issue #25, PR #51), com `use_profile`.
- Expurgo automático após 6 meses sem atualização e exclusão a pedido (PRs #51 e #52).
- Logs sem dado clínico.

### Fora (e por quê)
- Revogar o consentimento com um botão: hoje a pessoa desmarca condição por condição. Ficou como pendência (LGPD Art. 8º, §5º).
- Perfil lido da API quando houver conta (issue #22, fechada): no front o perfil de leitura continua o do aparelho. Conferir antes de afirmar o contrário.
- Verificação de idade: a data é autodeclarada, não há como comprovar.
- Comentário sobre peso: o app recolhe altura e peso, mas avisa que não comenta peso (persona Camila).

## Requisitos funcionais
- RF-01: o formulário (`web/src/telas/PerfilEdicao.tsx`) tem as seções Você, Saúde, Alimentação e Rotina, e todos os campos são opcionais; salvar vazio funciona.
- RF-02: marcar condição clínica sem marcar o consentimento mostra erro e não chama a API.
- RF-03: a API recusa condição sem `consent_health_data` verdadeiro.
- RF-04: data de nascimento de menor de 18 anos bloqueia o salvamento e leva a `/menor-de-idade`; a API responde 403 `age_restricted`.
- RF-05: data de nascimento no futuro é recusada, com mensagem de conferir a data (e não de menor de idade).
- RF-06: altura (50 a 250 cm) e peso (20 a 400 kg) são validados no front com os mesmos limites do schema.
- RF-07: o formulário avisa que o app não comenta peso.
- RF-08: o perfil é gravado na API (`PUT /api/v1/profile`, que substitui o perfil inteiro) e no aparelho; se a API recusar, nada é gravado local.
- RF-09: erro de rede não apaga o que a pessoa digitou.
- RF-10: o resumo (`Perfil.tsx`) mostra "Perfil salvo" por 3 segundos após salvar.
- RF-11: `GET /api/v1/profile` devolve 404 quando nunca houve perfil.
- RF-12: com `use_profile`, o `/check-claim` carrega o perfil; os avisos de gestante e condição crônica disparam mesmo sem constarem na pergunta.
- RF-13: perfil com condição marca a geração como dado sensível, e o gerador usa só o modelo próprio, nunca provedor externo.
- RF-14: falha ao buscar o perfil não derruba a checagem.
- RF-15: `DELETE /api/v1/profile` apaga o perfil e responde 204 mesmo sem perfil.
- RF-16: perfis sem atualização há mais de 6 meses são apagados por função SQL agendada.

## Requisitos não funcionais
- Privacidade nos logs: o log de perfil guarda só booleanos (`has_conditions`, `has_restrictions`, `consent_health_data`, `usado`), nunca a condição.
- Isolamento: RLS no Supabase, cada pessoa lê, grava, atualiza e apaga só o próprio perfil.
- Identificação por hash do usuário nos logs.
- Rate limit de escrita nas rotas de perfil.
- Formulário acessível e usável em 375 px (issue #28).

## Critérios de aceite
- [x] Salvar vazio, consentimento obrigatório, menor de 18, API 400, altura fora da faixa, data no futuro, carregar perfil salvo e erro de rede (`web/src/telas/PerfilEdicao.test.tsx`).
- [x] Resumo, aviso de sucesso de 3 s e aviso de dados só no aparelho (`web/src/telas/Perfil.test.tsx`).
- [x] Salvar, 404, substituição, perfil vazio, autenticação, consentimento, limites e data futura na API (`tests/test_profile.py`).
- [x] Log sem a condição clínica e com hash de usuário (`tests/test_profile.py`).
- [x] Exclusão: 204, 404 depois, sem apagar perfil alheio, exige autenticação, log sem conteúdo (`tests/test_exclusao_de_perfil.py`).
- [x] Perfil na checagem: avisos sem a pergunta, gestação, `use_profile`, geração sensível, falha do repositório, log sem conteúdo (`tests/test_perfil_na_checagem.py`).
- [x] Persistência Supabase (`tests/test_repositorio_perfil_supabase.py`).
- [x] RLS e expurgo escritos em `deploy/sql/001_profiles_e_feedback.sql`.
- [ ] Expurgo agendado e verificado em produção (o `cron.schedule` está comentado no SQL e exige a extensão pg_cron).
- [ ] Revogar o consentimento em um passo.
- [ ] Botão de apagar perfil no app (não encontrei chamada ao DELETE no front).
- [ ] Toque acidental no campo de data no iOS não cair como "menor de idade".

## Decisões
| Decisão | Por quê | Onde |
|---|---|---|
| Perfil 100% opcional | Coletar o mínimo; o app funciona sem perfil | `APP/schemas.py`, `PerfilEdicao.tsx` |
| Consentimento só com condição clínica | É o dado sensível do Art. 5º, II; restrição alimentar não exige | `APP/schemas.py`, `tests/test_profile.py` |
| PUT substitui, não mescla | Remover uma condição não exige verbo próprio | `APP/routers/profile.py` |
| 404 para "nunca preencheu" | Difere de "preencheu e está em branco" | `APP/routers/profile.py` |
| Condição sensível só no modelo próprio | Dado clínico não vai para provedor externo | `APP/model/pipeline.py` |
| DELETE devolve 204 sempre | Não revelar se havia dado a quem tiver o token | `APP/routers/profile.py` |
| Expurgo apaga a linha inteira | Sexo, altura, peso e nascimento juntos identificam | `deploy/sql/001_profiles_e_feedback.sql` |
| Se a API recusar, não grava local | Evita perfil local que a API não aceita | `PerfilEdicao.tsx` |
| Falha ao buscar perfil não derruba a checagem | Resposta genérica é melhor que nenhuma | `APP/routers/check_claim.py` |

## Riscos e limitações conhecidas
- Revogação indireta: sem botão, a pessoa pode não perceber como retirar o consentimento.
- Idade autodeclarada; toque acidental no campo de data no iOS pode cair como "menor de idade".
- Se o pg_cron não for ativado, o prazo de 6 meses não é cumprido.
- Sem conta, o perfil fica só no aparelho (aviso em `Perfil.tsx`).
- Os filtros dependem do que a pessoa escreve ou preenche; a persona Camila é detectada pelo texto, não pelo perfil.

## Referências
- Issues #19, #22, #25; PRs #47, #48, #51, #52.
- `Docs/Ethics/02_grupos_de_risco_e_filtros.md`
- `Docs/User/01_personas.md`, `Docs/User/02_acesso_e_canais.md`
- `Docs/Production/02_monitoramento_e_mlops.md` (logs sem dado clínico)
