# Contribuindo no front

Leia antes de pegar uma issue. São cinco regras curtas, e elas existem para o código de
cinco pessoas parecer escrito por uma.

## 1. A tela é sua, o resto é compartilhado

Cada issue entrega **uma tela inteira**, funcionando no navegador. Se precisar de algo
que não existe em `src/componentes/`, fale no grupo antes de criar: componente novo
afeta todo mundo, e é melhor combinarmos do que descobrirmos dois parecidos no mesmo PR.

Use a `src/telas/BoasVindas.tsx` como referência: estrutura de tela, componentes do
design system e estado do aparelho pelo `lib/armazenamento`.

## 2. Nada de `fetch` solto

Toda chamada passa por `src/lib/api/cliente.ts`. O erro chega na tela como `ErroDaApi`
com um código do contrato, e o texto que a pessoa lê está em `MENSAGEM_DE_ERRO`. Endpoint
novo entra no cliente, com o tipo em `tipos.ts`.

## 3. Nada de cor ou tamanho escrito na mão

Use as classes e as variáveis do design system (`src/estilos/claudinho.css`). Se faltar
alguma coisa, é sinal de que o design system precisa mudar primeiro: avise em vez de
inventar um `#hex` no componente.

## 4. Todo estado que a tela pode viver precisa existir

Antes de abrir o PR, confira: carregando, vazio, erro, texto longo, sem internet, e o
mesmo em tema escuro. O mock deixa provocar cada um (veja o README).

## 5. Acessibilidade não é polimento

O mínimo: alvo de toque com 48 px, rótulo visível em todo campo, foco que aparece, e
imagem com `alt`. Botão que só faz sentido com o ícone precisa de `aria-label`.

## Antes de mandar o PR

```bash
npm run lint && npm run format:check && npm test && npm run build
```

Escreva pelo menos um teste do comportamento que a pessoa vê, não do estado interno.
Os exemplos estão em `src/telas/BoasVindas.test.tsx` e `src/lib/api/cliente.test.ts`.

## Escrita

O texto da interface segue a seção 7 do design system: primeira pessoa, frase de
conversa, sem travessão, sem culpar quem come, e o botão diz a ação que acontece.
