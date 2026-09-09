from fastapi import FastAPI

from APP.errors import registrar_handlers
from APP.middleware import TraceMiddleware
from APP.observability import configurar_logging
from APP.ratelimit import registrar_rate_limit
from APP.routers import check_claim, feedback, health, profile

configurar_logging()

app = FastAPI(
    title="Claudinho \u2014 API de checagem de desinformacao nutricional",
    version="0.1.0",
    description=(
        "Challenge 1. O endpoint /check-claim ainda responde com dados MOCKADOS: "
        "o contrato esta congelado, o pipeline de RAG entra depois."
    ),
)

# O limite e aplicado por decorador em cada rota (ver APP/ratelimit.py), entao nao ha
# middleware do slowapi aqui. O TraceMiddleware e o mais externo: cronometra e registra
# inclusive as requisicoes barradas pelo rate limit.
registrar_rate_limit(app)
app.add_middleware(TraceMiddleware)

registrar_handlers(app)
app.include_router(health.router)
app.include_router(check_claim.router)
app.include_router(feedback.router)
app.include_router(profile.router)
