"""Divisão em trechos (chunking).

Função:
    Quebra o texto em trechos preservando os metadados de origem.

Responsabilidades:
    - Dividir com tamanho e sobreposição configuráveis
    - Manter a ligação de cada trecho com documento e página

Não deve:
    - Fixar tamanhos antes de testar com os documentos reais

Relações:
    Usa:        -
    Usado por:  rag.ingestion

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""

from dataclasses import dataclass

from rag.document_loader import LoadedDocument


@dataclass(frozen=True)
class DocumentChunk:
    """Representa um bloco de texto com seus metadados."""

    text: str
    metadata: dict


class TextChunker:
    """Divide documentos em chunks com sobreposição."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        """Inicializa o divisor com tamanho e sobreposição configuráveis."""

        if chunk_size <= 0:
            raise ValueError("O tamanho do chunk deve ser positivo.")

        if chunk_overlap < 0:
            raise ValueError("O overlap não pode ser negativo.")

        if chunk_overlap >= chunk_size:
            raise ValueError("O overlap deve ser menor que o tamanho do chunk.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(
        self,
        documents: list[LoadedDocument],
    ) -> list[DocumentChunk]:
        """Divide uma lista de documentos e retorna todos os chunks."""

        chunks = []

        for document in documents:
            chunks.extend(self._chunk_document(document))

        return chunks

    def _chunk_document(
        self,
        document: LoadedDocument,
    ) -> list[DocumentChunk]:
        """Divide um documento individual em chunks."""

        text = document.text

        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        chunk_index = 1

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Tenta encerrar o chunk em uma quebra de linha ou espaço.
            if end < len(text):
                split_at = text.rfind("\n", start, end)

                if split_at <= start + self.chunk_size // 2:
                    split_at = text.rfind(" ", start, end)

                if split_at > start + self.chunk_size // 2:
                    end = split_at

            chunk_text = text[start:end].strip()

            if chunk_text:
                metadata = dict(document.metadata)
                metadata["chunk_index"] = chunk_index

                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        metadata=metadata,
                    )
                )

                chunk_index += 1

            if end >= len(text):
                break

            next_start = end - self.chunk_overlap

            # Garante avanço para evitar um loop infinito.
            if next_start <= start:
                next_start = start + 1

            start = next_start

        return chunks
