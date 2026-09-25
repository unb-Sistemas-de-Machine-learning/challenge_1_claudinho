# Claudinho web

PWA de checagem de desinformação nutricional. Consome a API em `APP/`, e segue o design
system em [`../docs/Design/design-system.md`](../docs/Design/design-system.md).

## Rodando

Dois jeitos, e os dois valem.

### Sem backend, que é o padrão para mexer nas telas

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Abre em http://localhost:5173. **Não precisa de backend, Supabase nem LLM:** o
`.env.example` já vem com `VITE_API_MOCK=true`, e o mock responde o contrato inteiro,
inclusive os erros.

### Com a API de verdade, pelo Docker

Na raiz do repositório:

```bash
cp .env.example .env     # preencha SUPABASE_URL e SUPABASE_KEY
docker compose up --build
```

Sobe os dois containers: o front em http://localhost:5173 e a API em
http://localhost:8000. O código fica montado de fora, então salvar um arquivo recarrega
a página, sem rebuild. O mock fica desligado nesse modo, e o CORS da API já libera o
`localhost:5173` quando `APP_ENV=local`.

Se preferir sem Docker, rode `uvicorn APP.main:app --reload` na raiz e coloque
`VITE_API_MOCK=false` no `web/.env.local`.

> Desde o PR #15, a `Dev` responde com o pipeline de verdade, e não mais com dado fixo.
> Print e link são recusados com `422 input_nao_suportado`, de propósito: sem OCR e sem
> leitura de página, responder daria veredito confiante sobre o assunto errado.
>
> Apontar o app para staging ou produção hoje devolve 401 em toda chamada, porque o token
> é de desenvolvimento. A sessão anônima de verdade tem issue própria.

## O que já funciona

| Tela                                                    | Estado       |
| :------------------------------------------------------ | :----------- |
| Boas-vindas, com termos e confirmação de 18 anos        | Pronta       |
| Bloqueio para menor de 18                               | Pronta       |
| Checar, com texto, link e print                         | Pronta       |
| Carregando                                              | Pronta       |
| Resultado, com fontes, referências no texto e avaliação | Pronta       |
| Perfil, com resumo, aparência e privacidade             | Pronta       |
| Histórico, formulário do perfil, conta                  | Issue aberta |

A checagem e a avaliação já falam com a API de verdade. O perfil ainda lê do aparelho, e
a autenticação usa um token de desenvolvimento: as duas coisas têm issue própria.

## Comandos

| Comando                 | O que faz                                       |
| :---------------------- | :---------------------------------------------- |
| `npm run dev`           | Servidor de desenvolvimento                     |
| `npm test`              | Testes (Vitest e Testing Library)               |
| `npm run test:assistir` | Testes em modo contínuo                         |
| `npm run lint`          | Lint (oxlint)                                   |
| `npm run format`        | Formata com Prettier                            |
| `npm run build`         | Build de produção, gera o service worker do PWA |
| `npm run format:check`  | Confere a formatação, igual ao CI               |

## Como o código está organizado

| Pasta              | O que vive ali                                                                    |
| :----------------- | :-------------------------------------------------------------------------------- |
| `src/telas/`       | Uma tela por arquivo. É o que as issues pedem                                     |
| `src/componentes/` | Peças do design system, usadas pelas telas                                        |
| `src/lib/api/`     | Contrato (`tipos.ts`) e cliente (`cliente.ts`). Nenhuma tela chama `fetch` direto |
| `src/lib/`         | Estado do aparelho (`armazenamento.ts`), tema, mapa de vereditos                  |
| `src/mocks/`       | Mock da API, com os cinco vereditos e os erros do contrato                        |
| `src/estilos/`     | `claudinho.css` é cópia do design system. `app.css` é estrutura de tela           |

## Revendo o primeiro acesso

A tela de termos e confirmação de 18 anos aparece uma vez só: depois de aceitar, fica
gravado no aparelho. Para vê-la de novo, qualquer um destes serve:

- abrir `/boas-vindas` direto, que funciona mesmo já tendo aceitado;
- abrir em janela anônima, que mostra o primeiro acesso de verdade;
- rodar `localStorage.clear()` no console e recarregar, o que apaga também histórico,
  perfil e tema.

A tela de Perfil também tem o item "Termos de uso e limites", que abre a mesma tela em
modo leitura, com botão de voltar.

## Exercitando os estados de erro

Com o mock ligado, o código do erro vai no próprio texto da checagem:

| Escreva na checagem | Resposta                               |
| :------------------ | :------------------------------------- |
| `erro:401`          | Sessão expirada                        |
| `erro:413`          | Print acima de 5 MB                    |
| `erro:429`          | Limite de checagens, com `retry_after` |
| `erro:503`          | Serviço de respostas fora do ar        |

E o veredito segue o assunto: pão ou limão dá mito, café dá depende, arroz ou feijão dá
base científica, jejum extremo dá resposta de cuidado, e o resto dá faltam estudos.
