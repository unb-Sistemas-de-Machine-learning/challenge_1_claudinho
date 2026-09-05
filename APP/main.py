from fastapi import FastAPI

from APP.errors import registrar_handlers
from APP.middleware import LoggingDeInferencia
from APP.observabilidade import configurar_logging
from APP.routers import check_claim, health

app = FastAPI(
    title="Claudinho — API de checagem de desinformacao nutricional",
    version="0.1.0",
    description=(
        "Challenge 1. O endpoint /check-claim ainda responde com dados MOCKADOS: "
        "o contrato esta congelado, o pipeline de RAG entra depois."
    ),
)

configurar_logging()
app.add_middleware(LoggingDeInferencia)
registrar_handlers(app)
app.include_router(health.router)
app.include_router(check_claim.router)
