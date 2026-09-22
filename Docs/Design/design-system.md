---
title: Design System do Claudinho
description: Cores, tipografia, componentes, tom de voz e regras de produto do PWA de checagem de desinformação nutricional.
---

# Design System do Claudinho

Referência visual e de escrita do PWA que checa desinformação nutricional. O protótipo navegável usa exatamente estes valores, e o arquivo [`prototipo/claudinho.css`](./prototipo/claudinho.css) é a fonte da verdade: o que está escrito aqui foi tirado dele, não o contrário.

**Atualizado em:** 22 de setembro de 2026
**Arquivos:** [`Docs/Design/prototipo/`](./prototipo/) traz o protótipo (`prototipo.html`), esta documentação em versão navegável (`design-system.html`) e o CSS compartilhado (`claudinho.css`). Basta abrir os HTML no navegador.

---

## 1. Princípios

Saem das personas e da frente de Ética. Quando duas decisões de tela brigarem, estes desempatam.

1. **O veredito vem antes da explicação.** O Lucas decide em segundos se vai ler o resto. A frase do veredito cabe na primeira dobra, sem rolar.
2. **A fonte fica à mão, sem obrigar a abrir.** DOI e trecho usado estão sempre a um toque, numa seção que expande. Fonte visível é condição de confiança, não enfeite.
3. **Ninguém sai culpado por comer.** Nenhuma frase sugere que a pessoa errou. Mito vira alívio, não bronca. Peso nunca é comentado.
4. **Recusar também é cuidar.** Na recusa segura, a tela acolhe e oferece canal de ajuda no lugar do número pedido. É a tela da persona Camila.

---

## 2. Cores

A estratégia é contida: neutros claros em quase toda a tela, azul só nas ações e a cor forte guardada para o veredito. O fundo é um branco levemente quente em vez de `#FFFFFF`, que cansa menos a vista na tela do celular.

### 2.1. Por que azul, e por que não verde

A escolha veio de olhar a categoria, extraindo as cores do CSS dos próprios produtos:

| Produto | Cor de marca | Tipo de produto |
| :--- | :--- | :--- |
| Yuka | `#003388` azul-marinho | Dá um veredito |
| MyFitnessPal | `#0066EE` azul | Dá um veredito |
| Lifesum | `#21BA3A` verde | Conta calorias |
| Yazio | `#00AD85` verde-azulado, com pêssego `#F5AC70` | Conta calorias |
| Nutrium | `#62CDC0` turquesa | Software para nutricionista |
| Zoe | Neutros terrosos com amarelo `#FFD100` | Dá um veredito |

O padrão: **quem dá um veredito usa marca neutra ou azul** e deixa a escala semântica carregar o significado. **Quem conta calorias pode ter verde de marca** sem confundir ninguém. O Claudinho é do primeiro grupo, então verde, âmbar e vermelho ficam reservados ao veredito. O calor vem do pêssego, do mesmo jeito que o Yazio e a Zoe fazem.

### 2.2. Tokens

Os valores são definidos em OKLCH no CSS. Os hexadecimais abaixo são aproximações para ferramentas de design.

| Token | Claro | Escuro | Uso |
| :--- | :--- | :--- | :--- |
| `--c-ground` | `#FCFAF6` | `#18181C` | Fundo das telas |
| `--c-surface` | `#FFFFFD` | `#222228` | Campos e botões secundários |
| `--c-sunken` | `#F4F0E7` | `#0F0F13` | Bolha do usuário e trechos citados |
| `--c-ink` | `#373741` | `#F1F1F5` | Texto principal. 11,3:1 e 15,8:1 sobre o fundo |
| `--c-ink-2` | `#62626F` | `#C3C3CA` | Texto de apoio. 5,8:1 e 10,1:1 |
| `--c-ink-3` | `#686872` | `#A4A4AB` | Legendas. 5,3:1 e 7,1:1 |
| `--c-line` | `#E5E1D9` | `#3C3C43` | Divisórias |
| `--c-line-strong` | `#8B8B95` | `#797983` | Contorno de campo e chip. 3,4:1 e 3,7:1 |
| `--c-brand` | `#226FB3` | `#7ABDFF` | Ação principal e seleção. 5,1:1 com texto branco |
| `--c-brand-tint` | `#E0F1FF` | `#133555` | Fundo de aviso e chip selecionado |
| `--c-accent-bg` | `#FFE5CE` | `#482F1A` | Boas-vindas e resposta de cuidado |
| `--c-accent-ink` | `#7F4413` | `#FFCCA2` | Texto sobre o pêssego. 6,4:1 e 8,5:1 |

### 2.3. Cores de veredito

| Veredito | Fundo (claro) | Tinta (claro) | Contraste claro / escuro |
| :--- | :--- | :--- | :--- |
| `seguro` | `#D2F6DD` | `#17653C` | 6,1:1 / 8,6:1 |
| `cautela` | `#FFECB9` | `#875814` | 5,2:1 / 8,7:1 |
| `desinformacao` | `#FFE0DC` | `#B33736` | 4,8:1 / 8,0:1 |
| `sem_evidencia` | `#EFECE7` | `#5E5A53` | 5,8:1 / 8,6:1 |
| `recusa_segura` | `#FFE5CE` | `#7F4413` | 6,4:1 / 8,5:1 |

**Regras de cor**

- Cor nunca é o único sinal. Todo veredito leva ícone e rótulo escrito.
- O pêssego é acolhimento e convite. Nunca vira ação principal.
- Todo texto passa de 4,5:1 e todo contorno passa de 3:1, nos dois temas.

### 2.4. Os dois temas

O CSS trata três estados, não dois: escolha explícita de claro, escolha explícita de escuro, e o padrão, que segue o sistema.

```css
:root { /* paleta clara completa */ }

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* só os tokens mudam */ }
}

:root[data-theme="dark"] { /* mesma troca, para o seletor vencer */ }
```

No app, o seletor fica em **Perfil > Aparência**, com Automático, Claro e Escuro. No automático o atributo sai do HTML e o `prefers-color-scheme` volta a mandar.

---

## 3. Tipografia

Duas famílias com papéis que não se misturam.

- **Bricolage Grotesque**: frases de veredito, títulos de tela e a marca. Calorosa e um pouco informal, como alguém explicando em voz alta. Nunca em botões, rótulos ou campos.
- **Atkinson Hyperlegible Next**: texto corrido, interface e dados. Foi criada para baixa visão, e letras que não se confundem ajudam com brilho baixo no ônibus e com a leitura da persona Renata, de 54 anos.

| Papel | Família e peso | Tamanho | Classe |
| :--- | :--- | :--- | :--- |
| Veredito | Bricolage 700 | 30 / 32 px | `.verdict-headline` |
| Título de tela | Bricolage 700 | 28 / 31 px | `.h1` |
| Título de seção | Bricolage 650 | 22 / 26 px | `.h2` |
| Leitura | Atkinson 400 | 17 / 27 px | `.answer` |
| Interface | Atkinson 400 e 700 | 16 / 24 px | padrão |
| Apoio | Atkinson 400 | 15 / 22 px | `.small` |
| Legenda | Atkinson 400 | 13 / 18 px | `.caption` |

Campos de formulário usam 17 px ou mais, senão o iPhone dá zoom sozinho ao tocar.

---

## 4. Espaço e forma

Espaçamento em múltiplos de 4: **4, 8, 12, 16, 20, 24, 32, 48**. Margem lateral das telas: **20 px**.

O arredondamento carrega significado, em vez de ser um valor único repetido:

| Elemento | Raio | O que comunica |
| :--- | :--- | :--- |
| Bolha do usuário | 22 px, com o canto inferior direito em 6 px | Quem pergunta fala da direita |
| Resposta | 28 px, com o canto superior esquerdo em 6 px | O Claudinho responde da esquerda |
| Botões e chips | Pílula | Ação |
| Campos e avisos | 16 px | Entrada e informação |
| Trecho citado | 12 px | Conteúdo de terceiro |

---

## 5. Componentes

Todo alvo de toque tem pelo menos 48 px de altura, com exceção dos chips (44 px) e das referências numeradas, que ganham área invisível extra.

| Componente | Classe | Regras |
| :--- | :--- | :--- |
| Botão principal | `.btn.btn-primary` | Um por tela, no rodapé, ao alcance do polegar. O texto diz a ação |
| Botão secundário | `.btn.btn-secondary` | Contorno em `--c-line-strong`, fundo de superfície |
| Botão discreto | `.btn.btn-ghost` | Ações que não competem, como Agora não |
| Campo | `.input` | Rótulo sempre visível acima. Erro embaixo, dizendo como corrigir |
| Chip selecionável | `.chip` | Selecionado ganha tinta da marca e um visto, para não depender só da cor |
| Interruptor | `.switch` | Estado ligado em `--c-brand` |
| Bolha e resposta | `.bubble`, `.reply` | O par que forma a conversa. `data-verdict` define as duas cores |
| Selo de veredito | `.verdict-chip` | Versão compacta para o histórico |
| Fonte consultada | `.source` | Título, periódico, autores, DOI e trecho usado |
| Avaliação | `.feedback` | Motivo obrigatório quando a avaliação é negativa |
| Aviso | `.notice` | Variantes `care`, `warn`, `error`, `info`. Sempre no lugar do problema, nunca em pop-up |
| Barra de abas | `.tabbar` | Três destinos. Some nas telas de checagem e resultado |
| Progresso | `.steps` | Mostra a alegação extraída antes da resposta chegar |

Todo componente interativo precisa dos estados: padrão, foco visível, pressionado, desabilitado e carregando. Movimento entre 150 ms e 250 ms, e `prefers-reduced-motion` respeitado.

---

## 6. Vereditos

Cada valor de `verdict` da API tem rótulo, ícone, cor e um jeito próprio de abrir a frase.

| Valor na API | Quando | Rótulo e ícone | Como a frase abre | O que a tela acrescenta |
| :--- | :--- | :--- | :--- | :--- |
| `desinformacao` | `risk_score` acima de 0,65 | É mito, círculo com x | Alívio primeiro: "Pode respirar" | Fontes com DOI e botão Compartilhar |
| `seguro` | abaixo de 0,35 | Tem base científica, círculo com visto | "É verdade:" e o fato em linguagem simples | Fontes com DOI e botão Compartilhar |
| `cautela` | de 0,35 a 0,65 | Depende, balança | "Depende de..." e do quê | Aviso de evidência limitada (Ethics/03, seção 2.3) |
| `sem_evidencia` | Base sem cobertura | Faltam estudos, lupa com x | "Ainda não achei estudos..." | Explica que falta de estudo não é mentira nem verdade |
| `recusa_segura` | Guardrail de risco | Resposta de cuidado, mãos com coração | Diz o que não vai fazer e por quê, sem bronca | Canais de apoio (CVV 188, UBS, CRN), sem fontes e sem compartilhar |

Os limiares vivem em [`APP/verdict.py`](../../APP/verdict.py). O `risk_level` passa a sair de `APP/model/generator.py` quando o PR #15 entrar na `Dev`.

---

## 7. Tom de voz

Um amigo que entende do assunto. Fala na primeira pessoa, em frase de conversa, e nunca faz a pessoa se sentir boba por ter acreditado.

| Escreva assim | Evite | Por quê |
| :--- | :--- | :--- |
| Pode respirar: isso é mito. | Alegação classificada como desinformação. | Soa como sistema, não como gente |
| Não tem evidência de que isso queime gordura. | Os achados são inconclusivos quanto ao efeito termogênico. | Jargão citado na persona do Lucas |
| Esse jejum eu não vou calcular, porque ele pode te fazer mal. | Você não deveria fazer isso. | A recusa segura precisa ser não punitiva |
| Muitas checagens seguidas. Você pode checar de novo em 42 segundos. | Ops! Algo deu errado. | Erro vago não diz o que fazer |

**Regras de escrita**

- **Sem travessão.** Vírgula, dois-pontos ou ponto. Vale para interface, commits e documentação.
- **O botão diz o que acontece.** Checar, Salvar perfil, Enviar avaliação. A confirmação repete o verbo: Perfil salvo.
- **Nada de peso ou culpa.** As respostas não comentam peso, não usam "engorda" como ameaça e não chamam comida de veneno.
- **Informa, não prescreve.** Nada de dieta, dose ou plano. Quando o caso pede, a frase encaminha para um profissional.

---

## 8. Conta e histórico

Ninguém precisa criar conta para checar. A conta aparece quando ela passa a resolver um problema real da pessoa, que é não perder o que já foi salvo.

| Momento | O que acontece |
| :--- | :--- |
| Primeiro acesso | Termos, confirmação de 18 anos e pronto. A primeira tela nunca é um formulário de cadastro |
| Durante o uso | Histórico e perfil ficam no aparelho, e o app diz isso com todas as letras |
| Depois de 3 checagens | Convite dispensável no histórico, e uma seção no Perfil |
| Ao criar a conta | A tela mostra quantas checagens estão guardadas e avisa que nada se perde |

### 8.1. O que exige conta

| Ação | Precisa de conta? | Por quê |
| :--- | :--- | :--- |
| Checar por texto, link ou print | Não | É o valor do produto. Pedir cadastro antes de mostrar valor é o motivo mais comum de abandono no primeiro uso |
| Ver o histórico | Não | Fica no aparelho |
| Preencher o perfil de saúde | Não | O perfil protege quem pergunta. Condicioná-lo a cadastro afastaria justamente quem mais precisa do filtro |
| Levar histórico e perfil para outro aparelho | Sim | É o que a conta resolve |
| Apagar os dados do servidor | Sim | Sem identidade permanente não dá para atender um pedido de exclusão com segurança |

### 8.2. Como isso se sustenta no backend

- **Sessão anônima do Supabase.** O `signInAnonymously` cria um usuário de verdade, com JWT e claim `is_anonymous`. A API continua exigindo `Authorization: Bearer`, então o contrato não muda.
- **Conversão sem perder dado.** Ao criar a conta, o `updateUser` ou o `linkIdentity` anexa a identidade ao mesmo usuário. O `user_id` não muda, então perfil e feedback continuam apontando para a mesma pessoa.
- **Sessão anônima é fácil de criar em massa.** O limite por usuário de `APP/ratelimit.py` não basta sozinho: precisa conviver com limite por IP e CAPTCHA invisível no cadastro anônimo.
- **Limpeza não é automática.** Contas anônimas antigas ficam no banco até alguém apagar.
- **LGPD não muda por ser anônimo.** Condição clínica continua sendo dado sensível, então o consentimento explícito continua obrigatório.

---

## 9. Mobile e PWA

O produto é um PWA pensado para o celular de entrada, com uma mão, em sessões de um a dois minutos.

- **Compartilhar a partir do Instagram.** No Android, o PWA instalado entra no menu Compartilhar pelo `share_target` do manifest. No iPhone isso não existe, então Colar e Enviar print ficam sempre visíveis.
- **Convite para instalar.** Aparece dentro da tela inicial e pode ser dispensado. Nunca como pop-up na primeira visita.
- **Print acima de 5 MB.** O app reduz a imagem no aparelho antes de enviar. Só mostra erro se ainda passar do limite.
- **Sem internet.** A tela avisa, guarda o que foi escrito e desativa o botão Checar até a conexão voltar.
- **Polegar em primeiro lugar.** Botão principal fixo no rodapé, alvos de 48 px e respeito às áreas seguras do sistema.

```json
// manifest.webmanifest
"share_target": {
  "action": "/checar",
  "method": "POST",
  "enctype": "multipart/form-data",
  "params": {
    "text": "text",
    "url": "url",
    "files": [{ "name": "print", "accept": ["image/*"] }]
  }
}
```

---
