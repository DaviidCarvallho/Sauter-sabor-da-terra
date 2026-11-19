"""Repositório de documentos.

Função:
    Acesso aos arquivos das pastas certificacoes/, contratos/ e fichas_tecnicas/.

Responsabilidades:
    - Listar documentos e entregar seus bytes
    - Informar o tipo do documento a partir da pasta de origem

Não deve:
    - Extrair texto (função do rag.document_loader)

Relações:
    Usa:        storage (get_storage)
    Usado por:  rag.ingestion, services.documento_service

Status: implementado e testado (ver docs/ARQUITETURA_E_DECISOES_TECNICAS.md).
"""
from dataclasses import dataclass

from storage import get_storage
from storage.base import Storage


# Categorias de documentos aceitas pelo repositório.
DOCUMENT_CATEGORIES = {
    "certificacoes": "certificacao",
    "contratos": "contrato",
    "fichas_tecnicas": "ficha_tecnica",
}


@dataclass(frozen=True)
class DocumentInfo:
    """Informações básicas sobre um documento."""

    key: str
    name: str
    document_type: str


class DocumentRepository:
    """Gerencia o acesso aos documentos da cooperativa."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def list_documents(self) -> list[DocumentInfo]:
        """Lista os documentos das três categorias disponíveis."""

        documents = []

        for folder, document_type in DOCUMENT_CATEGORIES.items():
            keys = self._storage.list_keys(f"{folder}/")

            for key in keys:
                documents.append(
                    DocumentInfo(
                        key=key,
                        name=key.rsplit("/", 1)[-1],
                        document_type=document_type,
                    )
                )

        return documents

    def get_document_bytes(self, key: str) -> bytes:
        """Retorna o conteúdo binário de um documento."""

        self._validate_key(key)
        return self._storage.read_bytes(key)

    def get_document_type(self, key: str) -> str:
        """Identifica o tipo do documento pela pasta de origem."""

        self._validate_key(key)

        folder = key.split("/", 1)[0]
        return DOCUMENT_CATEGORIES[folder]

    @staticmethod
    def _validate_key(key: str) -> None:
        """Impede acesso a arquivos fora das categorias permitidas."""

        parts = key.split("/")

        if (
            len(parts) < 2
            or parts[0] not in DOCUMENT_CATEGORIES
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise ValueError(
                f"Chave de documento inválida: {key!r}"
            )
