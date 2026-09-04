from fastapi import APIRouter

from APP.config import obter_settings
from APP.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["infra"])
async def health() -> HealthResponse:
    """Liveness probe usada pelo provedor de hospedagem e pelo CI/CD."""
    return HealthResponse(status="ok", environment=obter_settings().app_env, version="0.1.0")
