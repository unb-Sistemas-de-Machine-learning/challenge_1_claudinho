# Spec: App PWA, telas e fluxo do usuário

> Documento consolidado em 07/10/2026 a partir do código, das issues e dos PRs. Registra o que foi construído, o que ficou de fora e por quê.

## Problema

Quem vê uma alegação de nutrição na internet (Instagram, TikTok, grupos de mensagem) não tem um jeito rápido de saber se ela se sustenta em estudos. Essa pessoa está no celular e não quer criar conta nem ler artigo científico.

## Objetivo

Oferecer um app instalável (PWA) em que a pessoa cola uma alegação, espera poucos segundos e recebe um veredito simples, com a explicação e as fontes (estudos com DOI). O uso é para maiores de 18 anos, funciona sem cadastro e guarda o histórico no próprio aparelho.

## Escopo

### Dentro

- Telas em `web/src/telas`: BoasVindas, Checar, Carregando, Resultado, Historico, Perfil, PerfilEdicao, Conta, Bloqueado.
- Cliente da API tipado (`web/src/lib/api`) e mock com MSW só em desenvolvimento (`web/src/mocks`).
- Armazenamento local (`web/src/lib/armazenamento.ts`): onboarding, rascunho, tema, histórico, perfil.
- PWA: manifest com ícones, convite de instalação, `share_target`, atualização automática, fallback de SPA na Vercel.
- Acessibilidade e layout em 375 px.

### Fora (e por quê)

- Envio de print: a API ainda não lê imagem. Desligado por `PRINT_DISPONIVEL = false` em `Checar.tsx` (PR #62).
- Link como entrada: a API ainda não lê página. Desligado por `LINK_DISPONIVEL = false`; link sozinho é recusado na hora, com mensagem (PR #62).
- Criação de conta e login: a tela `Conta` existe, mas está desligada, e o "Já tenho conta" some das boas-vindas (PR #63). As issues #23 e #24 (sessão anônima, conta) estão fechadas, mas a conta não está habilitada no app.
- Aparecer no menu de compartilhar do Instagram e do TikTok: o `share_target` está no manifest, mas na prática o app não aparece lá (PR #60, issue #27).
- Sincronização do histórico entre aparelhos: o histórico é só local.

## Requisitos funcionais

### Boas-vindas e bloqueio
- RF-01: a tela mostra os cinco termos homologados (Docs/Ethics/03).
- RF-02: o botão de começar só é liberado depois da confirmação de 18 anos.
- RF-03: "Tenho menos de 18" leva à tela de bloqueio (`/menor-de-idade`).
- RF-04: o texto "Sem cadastro para começar" informa que não há conta obrigatória.
- RF-05: o "Já tenho conta" não aparece enquanto a conta estiver desligada.

### Checar
- RF-06: a pessoa escreve ou cola o texto da alegação, com exemplos e botão Colar.
- RF-07: checagem vazia é recusada com mensagem que diz o que fazer.
- RF-08: link sozinho é recusado na hora, sem passar pela tela de espera. Link junto de texto segue para a checagem.
- RF-09: print e link não são oferecidos enquanto a API não os lê.
- RF-10: o rascunho sobrevive a erro e a cancelamento.
- RF-11: o convite de instalação usa o `beforeinstallprompt` e não promete aparecer no compartilhar de outros apps.

### Carregando
- RF-12: mostra os passos da checagem enquanto a requisição roda.
- RF-13: mostra "Entendi assim", a alegação extraída por `POST /extract-claim`, em paralelo com `POST /check-claim`.
- RF-14: se a extração falhar, a checagem segue normalmente.
- RF-15: cancelar aborta a requisição de verdade (`AbortController`); a resposta tardia não entra no histórico.
- RF-16: erro do serviço, limite de checagens e sessão expirada têm mensagem na tela, com opção de tentar de novo (PR #54).

### Resultado
- RF-17: cartão de veredito com o rótulo do veredito.
- RF-18: resposta com referências numeradas e lista de fontes com DOI.
- RF-19: a pessoa avalia a resposta e informa o motivo (`POST /feedback`).
- RF-20: compartilhar usa `navigator.share` e, sem ele, copia o texto.

### Histórico
- RF-21: lista local, uma linha por checagem, com data e rótulo do veredito, igual ao protótipo (PR #64).
- RF-22: sem itens, mostra estado vazio com botão que leva à checagem.
- RF-23: tocar num item abre `/resultado/<id>`.
- RF-24: apagar o histórico pede confirmação.

### Perfil
- RF-25: `Perfil` mostra resumo, aparência (tema) e privacidade.
- RF-26: `PerfilEdicao` é o formulário do perfil de saúde, com o consentimento da LGPD (PR #47).

## Requisitos não funcionais

- Funciona em 375 px de largura, com foco movido para o título a cada troca de tela (issue #28).
- Leitura do armazenamento tolera bloqueio (aba anônima), devolvendo o padrão.
- Instalável: manifest `display: standalone` com ícones 192, 512 e maskable, mais `apple-touch-icon`.
- Quem já abriu o app recebe a versão nova no acesso seguinte (`registerType: 'autoUpdate'`).
- O mock MSW não vai para o app publicado.
- Rotas profundas funcionam por fallback de SPA (`web/vercel.json`).
- Tema claro, escuro ou automático.

## Critérios de aceite

- [x] Os cinco termos aparecem nas boas-vindas (`BoasVindas.test.tsx`).
- [x] Começar só depois da confirmação de 18 anos (`BoasVindas.test.tsx`).
- [x] Sem "Já tenho conta" com a conta desligada (`BoasVindas.test.tsx`).
- [x] Fluxo da dúvida até a resposta com fonte e avaliação (`teste/fluxo.test.tsx`).
- [x] Checagem entra no histórico do aparelho (`teste/fluxo.test.tsx`).
- [x] Serviço fora do ar devolve a dúvida escrita; tentar de novo refaz a checagem (`teste/fluxo.test.tsx`).
- [x] Cancelar não deixa a resposta chegar depois nem entrar no histórico (`teste/fluxo.test.tsx`).
- [x] Checagem vazia é recusada (`teste/fluxo.test.tsx`).
- [x] Print não é oferecido; link sozinho é recusado na hora (`teste/fluxo.test.tsx`).
- [x] "Entendi assim" aparece e a falha da extração não trava (`Carregando.test.tsx`).
- [x] Histórico: estado vazio, itens, navegação e apagar (`Historico.test.tsx`).
- [x] Acessibilidade das telas (`telas/acessibilidade.test.tsx`).
- [x] Ícones do PWA e convite de instalação (`vite.config.ts`, `web/public`, PR #49).
- [x] Fallback de SPA (`web/vercel.json`).
- [ ] Print como entrada (depende da API ler imagem).
- [ ] Link como entrada (depende da API ler página).
- [ ] Conta habilitada no app.
- [ ] App aparecendo no compartilhar do Instagram e do TikTok.

## Decisões

| Decisão | Por quê | Onde |
|---|---|---|
| Usar sem conta, histórico e perfil no aparelho | Reduz atrito e dados pessoais; ver seção 8 do design system | `lib/armazenamento.ts`, `Docs/Design/design-system.md` |
| Desligar print e link por constante | A API não lê imagem nem página; mostrar o botão prometeria o que não existe | `Checar.tsx` (PR #62) |
| Esconder "Já tenho conta" | Conta desligada | `BoasVindas.tsx` (PR #63) |
| Confirmação de 18 anos antes de qualquer checagem | Termos homologados na ética | `BoasVindas.tsx`, `Docs/Ethics/03` |
| Extração em paralelo à checagem | Mostra "Entendi assim" enquanto a pessoa espera | `Carregando.tsx` (issue #26, PR #56) |
| Cancelamento com `AbortController` | Resposta tardia não pode aparecer nem ser guardada | `Carregando.tsx` (issue #32) |
| Id do histórico próprio, não o `trace_id` | O cache semântico repete o `trace_id` | `lib/armazenamento.ts` |
| Mock MSW só em desenvolvimento | Não pesar o app publicado | `main.tsx`, `vite.config.ts` |
| `registerType: 'autoUpdate'` | Atualização sem ação da pessoa | `vite.config.ts` |
| Histórico em lista, como o protótipo | Fidelidade ao design | `Historico.tsx` (PR #64) |

## Riscos e limitações conhecidas

- O `share_target` GET existe, mas na prática o app não aparece no compartilhar do Instagram e do TikTok.
- Com `autoUpdate`, a versão nova só chega no acesso seguinte ao primeiro.
- O histórico se perde se a pessoa limpar os dados do navegador ou trocar de aparelho.
- Armazenamento bloqueado faz o app voltar ao padrão (sem histórico persistente).
- O PR #58 (release da Dev na main) segue aberto na data deste documento.
- Não foi rodado nenhum teste ao escrever esta spec; os critérios citam testes que existem no código.

## Referências

- Issues #18, #20, #21, #26, #27, #28, #29 a #34.
- PRs #16, #17, #47, #49, #54, #56, #57, #60, #62, #63, #64.
- `Docs/Design/design-system.md` e `Docs/Design/prototipo/prototipo.html`.
- `Docs/Ethics/03_transparencia_e_disclaimers.md`.
- `web/src/lib/api/cliente.ts` e `tipos.ts` (contrato).
