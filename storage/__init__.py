"""Fábrica de armazenamento: a escolha do backend é feita por configuração."""

from functools import lru_cache

from storage.base import Storage
from storage.local_storage import LocalStorage
from utils.config import get_settings


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorage(settings.data_path)
    if settings.storage_backend == "gcs":
        raise NotImplementedError(
            "STORAGE_BACKEND=gcs ainda não foi implementado. "
            "Use STORAGE_BACKEND=local por enquanto."
        )
    raise ValueError(f"STORAGE_BACKEND inválido: {settings.storage_backend!r}")
