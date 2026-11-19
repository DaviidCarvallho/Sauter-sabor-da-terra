"""Ponto de entrada da aplicação.

Execução local (na pasta do projeto):
    uvicorn main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.chat_controller import router as chat_router
from api.health_controller import router as health_router
from utils.config import APP_VERSION, get_settings
from utils.logger import get_logger

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        description="Assistente inteligente para gestão de cooperativa agrícola.",
        version=APP_VERSION,
    )

    # Rotas da API primeiro; o mount "/" fica por último para não sobrescrevê-las.
    app.include_router(health_router)
    app.include_router(chat_router)
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    logger.info(
        "%s iniciado (env=%s, storage=%s)",
        settings.app_name,
        settings.app_env,
        settings.storage_backend,
    )
    return app


app = create_app()
