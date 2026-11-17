
"""Pipeline de ingestão.

Função:
    Constrói e reconstrói o índice vetorial a partir dos documentos
    da cooperativa.

Responsabilidades:
    - Listar documentos, carregar, dividir e armazenar.
    - Isolar falhas por documento.
    - Gerar relatório da execução.
    - Ser executável como comando (python -m rag.ingestion).

Não deve:
    - Rodar automaticamente a cada requisição do chat.
"""

from dataclasses import dataclass, field

from repositories.document_repository import DocumentRepository
from rag.chunker import TextChunker
from rag.document_loader import DocumentLoader
from rag.vector_store import VectorStore


@dataclass
class IngestionReport:
    """Resultado de uma execução do pipeline."""

    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    errors: list[str] = field(default_factory=list)


class Ingestion:
    """Coordena a ingestão dos documentos no índice vetorial."""

    def __init__(
        self,
        repository: DocumentRepository | None = None,
        loader: DocumentLoader | None = None,
        chunker: TextChunker | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.repository = (
            repository if repository is not None else DocumentRepository()
        )
        self.loader = loader if loader is not None else DocumentLoader()
        self.chunker = chunker if chunker is not None else TextChunker()
        self.vector_store = (
            vector_store if vector_store is not None else VectorStore()
        )

    def run(self) -> IngestionReport:
        """Executa a ingestão de todos os documentos disponíveis."""

        report = IngestionReport()

        documents = self.repository.list_documents()
        report.total_documents = len(documents)

        for document in documents:
            try:
                content = self.repository.get_document_bytes(document.key)

                loaded_documents = self.loader.load(
                    content=content,
                    filename=document.key,
                    document_type=document.document_type,
                )

                chunks = self.chunker.chunk_documents(loaded_documents)

                if not chunks:
                    raise ValueError(
                        "O documento não gerou nenhum chunk."
                    )

                self.vector_store.replace_document(
                    source=document.key,
                    chunks=chunks,
                )

                report.processed_documents += 1
                report.total_chunks += len(chunks)

            except Exception as error:
                report.failed_documents += 1
                report.errors.append(f"{document.key}: {error}")

        return report

def main() -> None:
    """Executa o pipeline de ingestão pela linha de comando."""

    ingestion = Ingestion()
    report = ingestion.run()

    print("\n=== Relatório de ingestão ===")
    print(f"Documentos encontrados: {report.total_documents}")
    print(f"Documentos processados: {report.processed_documents}")
    print(f"Documentos com falha: {report.failed_documents}")
    print(f"Chunks gerados: {report.total_chunks}")

    if report.errors:
        print("\n=== Erros ===")

        for error in report.errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
