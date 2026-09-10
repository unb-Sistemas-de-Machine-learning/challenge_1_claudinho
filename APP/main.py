from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from APP.auth import verificar_configuracao
from APP.config import obter_settings
from APP.errors import registrar_handlers
from APP.middleware import TraceMiddleware
from APP.observability import configurar_logging
from APP.ratelimit import registrar_rate_limit
from APP.routers import check_claim, feedback, health, profile

configurar_logging()
settings = obter_settings()
verificar_configuracao(settings)

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

# O app Expo roda em outra origem (localhost:8081 em desenvolvimento, dominio proprio
# na web), entao sem CORS o navegador barra toda chamada antes de sair da maquina.
# Em producao a lista de origens deve ser fechada, nunca "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "local" else settings.origens_permitidas,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Trace-Id", "Retry-After"],
)

registrar_handlers(app)
app.include_router(health.router)
app.include_router(check_claim.router)
app.include_router(feedback.router)
app.include_router(profile.router)
