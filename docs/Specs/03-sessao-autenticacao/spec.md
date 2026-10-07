# Spec: Sessão, autenticação, limite de uso e conta

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema
O Claudinho chama um LLM e uma busca vetorial a cada checagem, o que custa dinheiro. Sem identificar quem chama, qualquer um poderia martelar a API. Ao mesmo tempo, exigir cadastro antes da primeira checagem afastaria quem só quer tirar uma dúvida. Além disso, o perfil de saúde e a cota de uso precisam de uma identidade estável entre sessões.

## Objetivo
Dar a cada pessoa uma identidade sem fricção (login anônimo do Supabase), validar essa identidade em todos os endpoints, limitar o uso por identidade e deixar a criação de conta como evolução futura, desligada até que as condições técnicas existam.

## Escopo
### Dentro
- Validação do JWT do Supabase na API (`APP/auth.py`), por chaves públicas (JWKS) ou segredo HS256.
- Rate limit por identidade, com IP como reserva (`APP/ratelimit.py`).
- Sessão anônima no front (`web/src/lib/sessao.ts`): login, guarda e renovação do token.
- Espera do token pela camada de rede e mensagens para 401 e 429.
- Telas de conta (`Conta.tsx`), perfil (`Perfil.tsx`) e boas-vindas (`BoasVindas.tsx`), com a conta escondida.
- RLS nas tabelas de conhecimento (`articles`, `chunks`, `sources`).

### Fora (e por quê)
- Criar conta e entrar com e-mail e senha: desligado por `CONTA_DISPONIVEL = false` (PR #63). O Supabase só aceita senha de usuário anônimo depois de o e-mail ser confirmado, e sem SMTP próprio só entrega e-mail para a equipe do projeto, até 2 por hora.
- CAPTCHA no cadastro anônimo: exige enviar `captchaToken` pelo front antes de ligar no painel.
- Limpeza de usuários anônimos antigos: ainda não existe rotina.
- Redis para o rate limit: o contador em memória basta para uma instância (MVP).

## Requisitos funcionais
- RF-01: todo endpoint da API (check-claim, extract-claim, feedback, profile) exige `Authorization: Bearer <token>`; sem token a resposta é 401.
- RF-02: a API recusa token expirado, de assinatura inválida, de audiência errada, sem `sub`, com algoritmo `none` ou com confusão de algoritmo.
- RF-03: a identidade devolvida é o `sub` do usuário, estável entre renovações do token.
- RF-04: o modo local (qualquer token não vazio) só vale com `APP_ENV=local`; o padrão de `APP_ENV` é produção.
- RF-05: se as chaves públicas não puderem ser buscadas, a API responde 503, não 401.
- RF-06: o limite de checagem é de 10 por minuto e o de escrita de 30 por minuto, por identidade, em janela deslizante.
- RF-07: sem token válido, o balde do limite é o IP do cliente.
- RF-08: ao estourar o limite, a API responde 429 com `retry_after` no corpo e `Retry-After` no header, com o tempo real até liberar.
- RF-09: o limite é aplicado antes da autenticação da rota e conta também requisições sem token ou com corpo inválido.
- RF-10: ao abrir o app, o front faz `signInAnonymously`, reaproveita sessão existente e atualiza o token quando o Supabase renova.
- RF-11: o app monta sem esperar o Supabase; a primeira requisição espera o token por até 8 s e depois segue sem ele.
- RF-12: 401 mostra "feche e abra o app" e 429 volta para a tela de checar com o tempo de espera.
- RF-13: com `CONTA_DISPONIVEL = false`, as telas não oferecem criar conta nem "Já tenho conta".
- RF-14: `articles`, `chunks` e `sources` têm RLS ligado, com política só de leitura para `anon` e `authenticated`.

## Requisitos não funcionais
- Falha fechada: configuração esquecida nunca desliga a autenticação.
- O token é validado uma vez por requisição, em threadpool, para a busca de chave pública não travar o event loop.
- Falha de login ou exceção do SDK não derrubam o app.
- Nenhum segredo no repositório: a validação por JWKS não exige segredo.
- A mesma identidade (hash) liga o balde do limite ao `user_id_hash` do log de inferência.

## Critérios de aceite
- [x] Sem header, token expirado, assinatura de outro segredo, audiência errada e sem `sub` dão 401 (`tests/test_auth.py`).
- [x] A identidade sobrevive à renovação do token e um usuário não enxerga o perfil do outro (`tests/test_auth.py`).
- [x] Token ES256 válido passa; chave desconhecida, algoritmo `none`, HS256 sem segredo e confusão de algoritmo são recusados (`tests/test_auth_jwks.py`).
- [x] Falha ao buscar as chaves responde 503 (`tests/test_auth_jwks.py`).
- [x] Sem `APP_ENV` o padrão é produção; valor escrito errado não sobe (`tests/test_auth_fail_closed.py`).
- [x] Token validado uma vez por requisição e busca lenta de chave não derruba a API (`tests/test_auth_fail_closed.py`).
- [x] O limite barra a requisição seguinte, separa usuários e não zera ao renovar o token (`tests/test_ratelimit.py`).
- [x] Requisição sem token e corpo inválido também contam; `retry_after` acompanha a janela (`tests/test_ratelimit.py`).
- [x] Escrita não consome a cota do check-claim (`tests/test_ratelimit.py`).
- [x] O front entra anônimo, reaproveita sessão, atualiza o token e não acumula ouvintes (`web/src/lib/sessao.test.ts`).
- [x] Falha de login e exceção do SDK não derrubam o app (`web/src/lib/sessao.test.ts`).
- [x] A primeira requisição sai com o token que chegou depois de o app montar (`web/src/lib/api/cliente.sessao.test.ts`).
- [x] Telas de conta têm teste de componente (`web/src/telas/Conta.test.tsx`, `BoasVindas.test.tsx`).
- [ ] CAPTCHA (Turnstile) no cadastro anônimo.
- [ ] Limpeza de usuários anônimos antigos.
- [ ] Criar conta e entrar funcionando em produção (depende de SMTP).
- [ ] Teste automatizado para o RLS das tabelas de conhecimento (a correção foi feita em 06/10 direto no banco).

## Decisões
| Decisão | Por quê | Onde |
| :--- | :--- | :--- |
| Login anônimo do Supabase em vez de cadastro obrigatório | Zero fricção na primeira checagem e identidade para perfil e cota | `web/src/lib/sessao.ts`, PR #60 |
| Validar por JWKS (ES256/RS256), HS256 só se houver segredo | Projetos novos assinam com chave assimétrica e não há segredo a configurar | `APP/auth.py` |
| `APP_ENV` padrão produção; modo local só com `APP_ENV=local` | Falha fechada: segredo vazio já não significa "auth desligada" | `APP/auth.py` |
| Identidade é o `sub`, não o token | O token rotaciona a cada hora; perfil e cota não podem sumir | `APP/auth.py`, `APP/ratelimit.py` |
| Limite como dependência de rota, não decorador | Só assim conta tráfego sem token e com corpo inválido | `APP/ratelimit.py` |
| Janela deslizante e `retry_after` real | Janela fixa permite o dobro na virada; "tente em 60 s" geraria laço de 429 | `APP/ratelimit.py` |
| Login anônimo suspenso e depois religado | O time achou que era pago (issue #23); a página de preços lista "Anonymous Sign-ins: Included" no Free | issue #23, PR #60 |
| Conta desligada por `CONTA_DISPONIVEL = false` | Senha de anônimo exige e-mail confirmado e o Supabase sem SMTP próprio limita a entrega | `web/src/lib/sessao.ts`, PR #63 |
| RLS só leitura nas tabelas de conhecimento | Estavam abertas para escrita pela chave pública embutida no app | Supabase (06/10/2026) |
| App monta sem esperar o Supabase; rede espera até 8 s | Tela branca em rede lenta é pior que uma mensagem de sessão | `web/src/lib/api/cliente.ts` |

## Riscos e limitações conhecidas
- Só Owner ou Administrator do projeto Supabase liga o login anônimo no painel.
- Sem CAPTCHA, o cadastro anônimo é aberto; o freio é o limite de 30 cadastros por hora por IP (padrão do Supabase).
- Usuários anônimos antigos se acumulam sem rotina de limpeza.
- O contador em memória não é compartilhado: com mais de uma instância, o limite multiplica. Trocar por Redis (Upstash) está previsto em `APP/ratelimit.py`.
- Quem está atrás do mesmo NAT divide o balde de IP quando não há token.
- Perder a sessão anônima (limpar dados do navegador) perde o perfil, enquanto não houver conta.

## Referências
- Código: `APP/auth.py`, `APP/ratelimit.py`, `web/src/lib/sessao.ts`, `web/src/lib/api/cliente.ts`, `web/src/telas/Conta.tsx`, `Perfil.tsx`, `BoasVindas.tsx`.
- PRs: #6 (JWT, rate limit e perfil), #54 (limite e sessão expirada na tela), #60 (sessão anônima), #63 (esconde "Já tenho conta").
- Issues: #20, #23, #24, #37.
- Docs: `Docs/Design/design-system.md` (seção 8), `Docs/Production/01_plataforma_e_deploy.md`, `Docs/Production/03_escalabilidade_e_desempenho.md`.
