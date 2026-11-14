from fastapi import APIRouter

from models.health_model import HealthResponse
from utils.config import APP_VERSION, get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Verifica se a aplicação está no ar e como está configurada (sem expor segredos)."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=APP_VERSION,
        environment=settings.app_env,
        storage_backend=settings.storage_backend,
        ai_configured=settings.ai_configured,
    )
