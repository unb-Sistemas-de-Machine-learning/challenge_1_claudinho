# Servico de embeddings (Hugging Face Spaces)

> **Alternativa, não o padrão.** Por padrão a API usa a API de inferência do Hugging Face,
> que não exige Space (`EMBEDDINGS_PROVEDOR=hf-inference`). Este serviço só vale a pena se a
> cota gratuita da API acabar e alguém do grupo tiver conta PRO, que é o que o Hugging Face
> exige para criar Spaces Docker. Nesse caso, use `EMBEDDINGS_PROVEDOR=space`.

Tira o modelo `intfloat/multilingual-e5-base` de dentro da API. Sem ele, a API carrega o
torch e o modelo (mais de 1,5 GB) e não cabe na Vercel (500 MB por função) nem no Render
gratuito (512 MB de RAM). Com ele, a API fica leve e só faz uma chamada HTTP por consulta.

É o **mesmo modelo** com que a base foi indexada, então não há reindexação.

## Como subir

Mesmo processo do Space do Ollama (`deploy/ollama-space/README.md`):

1. Em https://huggingface.co/new-space, crie um Space com SDK **Docker**, template
   *Blank*, hardware **CPU basic** e visibilidade **Private**.
2. Envie os três arquivos desta pasta: `Dockerfile`, `app.py` e `requirements.txt`.
3. Espere o build (alguns minutos: ele baixa o torch e o modelo).
4. Teste:

       curl -X POST https://<usuario>-<space>.hf.space/embed \
         -H "Authorization: Bearer hf_..." -H "Content-Type: application/json" \
         -d '{"textos": ["query: agua com limao emagrece?"]}'

   A resposta tem `"dimensao": 768`.

5. Na API (Vercel, Render ou `.env` local):

       EMBEDDINGS_URL=https://<usuario>-<space>.hf.space
       EMBEDDINGS_TOKEN=hf_...

Pode usar o mesmo token de leitura do Space do Ollama.

## Space dormindo

Space gratuito dorme depois de um período sem uso, e a primeira chamada depois disso
demora enquanto ele acorda. Nesse caso a API responde **503** ("busca de estudos
indisponível, tente de novo em instantes"), e não uma resposta de "sem evidência", que
seria falsa: a base tem os estudos, só o serviço estava parado.
