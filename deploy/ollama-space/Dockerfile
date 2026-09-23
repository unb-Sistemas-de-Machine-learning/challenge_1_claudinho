# LLM proprio do Claudinho: Ollama servindo um modelo aberto no Hugging Face Spaces.
# O modelo e baixado no build, entao o Space ja sobe pronto, sem download a cada inicio.

# Fixe uma versao (ex.: ollama/ollama:0.12.3) depois do primeiro build que funcionar:
# com "latest", um rebuild pode trocar o comportamento sem nenhum commit.
FROM ollama/ollama:latest

ARG MODELO=qwen2.5:3b

# 7860 e a porta que o Hugging Face Spaces expoe.
# CONTEXT_LENGTH: o padrao do Ollama corta o prompt em silencio, e o prompt do RAG
#   (instrucoes + 5 chunks) passa facil de 2 mil tokens.
# KEEP_ALIVE=-1: mantem o modelo na memoria; recarregar custa uns 10 s por pergunta.
# NUM_PARALLEL=1: com 2 vCPU, duas geracoes ao mesmo tempo so deixam as duas lentas.
ENV OLLAMA_HOST=0.0.0.0:7860 \
    OLLAMA_MODELS=/opt/ollama/models \
    OLLAMA_CONTEXT_LENGTH=8192 \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_NUM_PARALLEL=1

RUN ollama serve & pid=$!; \
    for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done; \
    ollama pull "$MODELO" && kill $pid

# O Spaces roda o container com o uid 1000, sem permissao nas pastas do root.
RUN chmod -R a+rX /opt/ollama && mkdir -p /home/user && chmod 777 /home/user
ENV HOME=/home/user
USER 1000

EXPOSE 7860
CMD ["serve"]
