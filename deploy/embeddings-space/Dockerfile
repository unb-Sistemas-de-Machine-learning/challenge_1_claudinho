# Servico de embeddings para o Hugging Face Spaces (SDK Docker, CPU basic).
FROM python:3.12-slim

# O Spaces roda o container com o usuario de uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface
WORKDIR /home/user/app

# torch so de CPU: a versao padrao traz 3+ GB de bibliotecas NVIDIA inuteis aqui.
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Modelo baixado no build, nao a cada inicio do container.
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('intfloat/multilingual-e5-base')"

COPY --chown=user app.py .

EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
