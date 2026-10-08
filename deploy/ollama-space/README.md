---
title: Claudinho LLM
emoji: 🥗
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# LLM próprio do Claudinho (Ollama no Hugging Face Spaces)

Serve um modelo aberto (`qwen2.5:3b` por padrão) com a API compatível com a OpenAI do
Ollama. A API do Claudinho chama esse Space primeiro e só usa o Gemini ou a OpenAI como
reserva (ver `APP/model/llm.py`).

O cabeçalho YAML acima é lido pelo Hugging Face: ele precisa ficar no topo do README
**dentro do repositório do Space**.

## Por que este modelo

| Modelo | Tamanho | Observação |
|---|---|---|
| `qwen2.5:3b` (padrão) | ~1,9 GB | Melhor equilíbrio entre português, respeito ao JSON e velocidade em CPU |
| `gemma3:4b` | ~3,3 GB | Texto mais natural, cerca de 40% mais lento |
| `llama3.2:3b` | ~2,0 GB | Alternativa; português um pouco pior |

Modelos de 7B ou mais passam de 1 minuto por resposta nas 2 vCPUs gratuitas.

Para trocar o modelo, mude o `ARG MODELO` no `Dockerfile` e a variável `LLM_MODELO` da
API para o mesmo nome.

## Como publicar

1. Em https://huggingface.co/new-space, crie um Space com **SDK Docker**, modelo
   *Blank*, hardware **CPU basic (gratuito)** e visibilidade **Private**.
2. Na aba **Files** do Space, use **Add file → Upload files** para enviar o `Dockerfile`
   e este `README.md` (substituindo o README gerado pelo Hugging Face).
3. Espere o build terminar (alguns minutos, por causa do download do modelo).
4. Em https://huggingface.co/settings/tokens, crie um token do tipo **Read**.
5. No `.env` da API:

   ```
   LLM_BASE_URL=https://<usuario>-claudinho-llm.hf.space/v1
   LLM_MODELO=qwen2.5:3b
   LLM_API_KEY=hf_...
   ```

## Por que privado

O Ollama não tem autenticação. Num Space público, qualquer pessoa usaria as 2 vCPUs e
deixaria o Claudinho na fila. No Space privado, o próprio Hugging Face exige o token no
header `Authorization: Bearer`, que é o mesmo header que a API já manda.

## Testar

```bash
curl https://<usuario>-claudinho-llm.hf.space/v1/chat/completions \
  -H "Authorization: Bearer hf_..." -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:3b", "messages": [{"role": "user", "content": "Ovo faz mal?"}]}'
```

## Limitações do plano gratuito

- **Só CPU:** de 20 a 60 s por resposta. Por isso a API espera até `LLM_TIMEOUT_S` (90 s).
- **Hiberna após 48 h sem uso.** A primeira chamada depois disso espera o Space subir.
  Antes de uma apresentação, faça uma requisição para acordá-lo.
- **Uma geração por vez** (`OLLAMA_NUM_PARALLEL=1`). Com muita gente usando ao mesmo
  tempo, as requisições passam do tempo limite e a API cai para a reserva externa.
