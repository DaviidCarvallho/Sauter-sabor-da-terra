"""Configuração centralizada da aplicação.

Todas as variáveis de ambiente são lidas aqui, uma única vez. O restante do
código importa `get_settings()` e nunca acessa `os.environ` diretamente.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    """Variáveis de ambiente tipadas. Valores padrão servem ao ambiente local."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Aplicação
    app_name: str = "Sabor da Terra"
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"

    # IA (usada a partir da etapa dos agentes)
    google_api_key: SecretStr | None = None
    model: str | None = None

    # Armazenamento de arquivos (local agora, GCS depois)
    storage_backend: Literal["local", "gcs"] = "local"
    data_dir: Path = Path("data")
    gcs_bucket: str | None = None
    gcs_prefix: str = ""

    # Índice vetorial (ChromaDB). Fica fora de data/ e do Git.
    vector_store_dir: Path = Path(".vectorstore")

    @field_validator("google_api_key", "model", "gcs_bucket", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        """`CHAVE=` vazia no .env deve contar como não configurada."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def data_path(self) -> Path:
        """Pasta de dados como caminho absoluto, independente de onde o servidor é iniciado."""
        return self.data_dir if self.data_dir.is_absolute() else BASE_DIR / self.data_dir

    @property
    def vector_store_path(self) -> Path:
        path = self.vector_store_dir
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def ai_configured(self) -> bool:
        """True quando chave e modelo foram informados (não valida a chave)."""
        return self.google_api_key is not None and self.model is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
