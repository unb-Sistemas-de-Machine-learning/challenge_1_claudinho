from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from APP.auth import preparar_chaves_publicas, verificar_configuracao
from APP.config import obter_settings
from APP.errors import registrar_handlers
from APP.middleware import LoggingDeInferencia
from APP.observabilidade import configurar_logging
from APP.routers import check_claim, feedback, health, profile

app = FastAPI(
    title="Claudinho — API de checagem de desinformacao nutricional",
    version="0.1.0",
    description=(
        "Checagem de desinformação nutricional com RAG sobre literatura científica. "
        "Cada resposta cita os estudos recuperados e não substitui profissional de saúde."
    ),
)

settings = obter_settings()
# Derruba a subida se o ambiente nao estiver pronto, em vez de deixar a API responder
# com a autenticacao desligada ou com o CORS barrando o app inteiro.
verificar_configuracao(settings)
preparar_chaves_publicas(settings)

configurar_logging()
app.add_middleware(LoggingDeInferencia)
# O app e um PWA em outro dominio, entao sem CORS o navegador bloqueia toda chamada.
# O fallback de desenvolvimento e amarrado a APP_ENV=local, e nao a "lista vazia": com
# `or`, uma variavel esquecida em producao liberaria localhost em vez de nao liberar nada.
ORIGENS_DE_DESENVOLVIMENTO = ["http://localhost:5173", "http://localhost:8081"]
origens = ORIGENS_DE_DESENVOLVIMENTO if settings.app_env == "local" else settings.origens_permitidas
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
registrar_handlers(app)
app.include_router(health.router)
app.include_router(check_claim.router)
app.include_router(feedback.router)
app.include_router(profile.router)
