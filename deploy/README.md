# Deploy do Claudinho

```
App (Expo) ──HTTPS──> API (Vercel) ──> Supabase (dados + pgvector)
                          │
                          ├──> API de inferência do Hugging Face  (embeddings, e5-base)
                          └──> Space do Ollama (deploy/ollama-space) ──reserva──> Gemini
```

A API **não carrega nenhum modelo**. É isso que a faz caber na Vercel: sem o
`sentence-transformers`, o runtime ocupa cerca de 64 MB, contra 4,4 GB antes, e o limite
da Vercel é 500 MB por função.

---

## 1. Embeddings

Não há o que hospedar: a API de inferência do Hugging Face roda o mesmo
`intfloat/multilingual-e5-base` com que a base foi indexada.

1. Em https://huggingface.co/settings/tokens, crie um token **Fine-grained** com a
   permissão **"Make calls to Inference Providers"**.
2. Use esse token em `EMBEDDINGS_TOKEN` (tabela abaixo).

**Cota:** conta gratuita tem US$ 0,10 por mês em créditos, **sem pagamento de excedente**:
quando acaba, as chamadas param até o mês virar, e a API passa a devolver 503 (o log mostra
`"detalhe": "HTTP 402"`). O consumo pode ser acompanhado em
https://huggingface.co/settings/billing. Se a cota não bastar, as saídas são o PRO
(US$ 9/mês, com excedente pago) ou o Space próprio de `deploy/embeddings-space`, que também
exige PRO para ser criado.

## 2. Space do Ollama

Siga `deploy/ollama-space/README.md` (já no ar pela Beatriz).

## 3. API na Vercel

1. Em https://vercel.com/new, importe o repositório do GitHub.
2. **Root Directory:** a raiz do repositório (onde estão `vercel.json` e `api/`).
3. **Framework Preset:** deixe a Vercel detectar (Python/FastAPI). Não configure comando
   de build nem de instalação: ela instala pelo `pyproject.toml`.
4. Em **Environment Variables**, cadastre as variáveis da tabela abaixo.
5. Clique em **Deploy**.

### Variáveis de ambiente

| Variável | Valor | Obrigatória |
|---|---|---|
| `APP_ENV` | `production` | Sim |
| `SUPABASE_URL` | URL do projeto Supabase | Sim |
| `SUPABASE_KEY` | chave do Supabase | Sim |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT Secret (legado) | Só em projeto antigo, que assina tokens com HS256. Projetos criados desde outubro de 2025 usam chaves assimétricas, e a API valida pelas chaves públicas do `SUPABASE_URL`, sem segredo |
| `EMBEDDINGS_URL` | `https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-base/pipeline/feature-extraction` | Sim: sem ela, a API tenta carregar o modelo localmente e falha |
| `EMBEDDINGS_TOKEN` | token Fine-grained com "Make calls to Inference Providers" | Sim |
| `LLM_BASE_URL` | `https://<usuario>-<space>.hf.space/v1` (Space do Ollama) | Recomendada |
| `LLM_API_KEY` | token de leitura do Hugging Face | Se o Space for privado |
| `GEMINI_API_KEY` | chave do Gemini | Reserva do Ollama |
| `ORIGENS_PERMITIDAS` | `["https://seu-projeto.vercel.app"]`, com colchetes e aspas duplas | **Sim**: sem ela, a API se recusa a subir fora do modo local |

### Conferindo

    curl https://<projeto>.vercel.app/health

Deve responder `{"status": "ok", "environment": "production", ...}`. A documentação
interativa fica em `https://<projeto>.vercel.app/docs`.

Depois, rode o teste de estresse contra o deploy para medir a latência real:

    uv run python -m benchmarks.estresse --url https://<projeto>.vercel.app --usuarios 3 --requisicoes 6

(Em produção o JWT é validado, então o estresse com identidades falsas vai receber 401.
Para medir com JWT real, use o benchmark com `--token`.)

---

## O que se comporta diferente na Vercel

A Vercel roda a API em instâncias que sobem e somem conforme a demanda. Três efeitos:

- **Perfil e feedback em memória.** Os dois repositórios ainda são os em memória
  (`APP/repositorios/perfil.py` e `APP/repositorios/feedback.py`), esperando as tabelas
  `profiles` e `feedback` no Supabase; o passo a passo está no docstring de cada
  `RepositorioSupabase`. Na Vercel, um perfil ou feedback salvo numa requisição pode não
  existir na seguinte. **Precisam das tabelas antes de serem usados de verdade.**
- **Rate limit por instância.** O contador fica na memória de cada instância, então o limite
  de 10/min vale por instância, não por usuário no total. Aceitável para o MVP; para valer de
  verdade, o contador vai para o Redis (Upstash), como previsto no `Docs/Production/03`.
- **Primeira chamada lenta.** Instância nova (cold start) e Space do Ollama dormindo somam
  atraso na primeira checagem depois de um tempo parado. Se os embeddings não responderem
  (ou a cota do mês acabar), a API devolve **503**, e não uma falsa resposta de
  "sem evidência".

---

## Alternativa: Render

Se a Vercel der problema, o mesmo código sobe no Render pelo `Dockerfile`, que também não
instala mais o torch:

1. https://dashboard.render.com → **New → Web Service** → conecte o repositório.
2. **Runtime:** Docker. **Plan:** Free.
3. As mesmas variáveis de ambiente da tabela acima.

O Render roda um processo contínuo, então o perfil em memória e o rate limit se comportam
de forma consistente enquanto ele está acordado. Em compensação, o plano gratuito dorme
após 15 minutos sem uso, e o primeiro acesso depois disso demora para acordar.

---

## Desenvolvimento local

Sem `EMBEDDINGS_URL`, a API usa o modelo local. Instale as dependências de ML:

    uv pip install -r requirements-dev.txt -r requirements-ml.txt

Com `EMBEDDINGS_URL` preenchida, basta o `requirements-dev.txt`, mas cada checagem gasta
a cota gratuita do Hugging Face.
