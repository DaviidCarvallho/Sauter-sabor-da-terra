"""Recuperador.

Função:
    Busca os trechos mais relevantes para uma pergunta.

Responsabilidades:
    - Consultar o vector_store (top-k) e devolver trecho, fonte e score
    - Filtrar por metadados quando útil (tipo de documento, produtor)

Não deve:
    - Gerar a resposta final (função do agente)

Relações:
    Usa:        rag.vector_store, models.documento_model
    Usado por:  services.documento_service

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""


"""Recuperador de trechos relevantes para consultas RAG."""

from dataclasses import dataclass

from rag.chunker import DocumentChunk
from rag.vector_store import VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    """Representa um chunk recuperado e sua distância."""

    chunk: DocumentChunk
    distance: float


class Retriever:
    """Gerencia a recuperação de informações relevantes."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Recebe a instância do armazenamento vetorial."""

        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        max_distance: float | None = None,
    ) -> list[RetrievedChunk]:
        """Recupera os chunks mais relevantes para uma pergunta."""

        if not query.strip():
            raise ValueError("A consulta não pode estar vazia.")

        if top_k <= 0:
            raise ValueError("top_k deve ser maior que zero.")

        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance não pode ser negativo.")

        results = self.vector_store.search(
            query=query,
            n_results=top_k,
        )

        retrieved_chunks = []

        for chunk, distance in results:
            if max_distance is not None and distance > max_distance:
                continue

            retrieved_chunks.append(
                RetrievedChunk(
                    chunk=chunk,
                    distance=distance,
                )
            )

        return retrieved_chunks
