# Versao fixada em .python-version — mantenha os dois iguais.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias primeiro: essa camada so e reconstruida quando o requirements muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY APP ./APP

# Roda sem privilegios de root.
RUN useradd --create-home --uid 1000 claudinho && chown -R claudinho:claudinho /app
USER claudinho

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# Render e Fly injetam a porta via $PORT.
CMD ["sh", "-c", "uvicorn APP.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
