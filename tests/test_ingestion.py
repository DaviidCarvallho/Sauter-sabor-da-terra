import pytest

from types import SimpleNamespace

from rag.chunker import DocumentChunk
from rag.ingestion import Ingestion

@pytest.fixture


def sample_documents():
    return [
        SimpleNamespace(
            key="certificacoes/certificado.pdf",
            name="certificado.pdf",
            document_type="certificacao",
        ),
        SimpleNamespace(
            key="contratos/contrato.pdf",
            name="contrato.pdf",
            document_type="contrato",
        ),
    ]

@pytest.fixture
def fake_repository(sample_documents):
    class FakeRepository:
        def list_documents(self):
            return sample_documents

        def get_document_bytes(self, key):
            return f"Conteúdo de {key}".encode("utf-8")

    return FakeRepository()

@pytest.fixture
def fake_loader():
    class FakeLoader:
        def load(self, content, filename, document_type):
            return [
                SimpleNamespace(
                    text=content.decode("utf-8"),
                    metadata={
                        "source": filename,
                        "document_type": document_type,
                        "page": 1,
                    },
                )
            ]

    return FakeLoader()

@pytest.fixture
def fake_chunker():
    class FakeChunker:
        def chunk_documents(self, documents):
            chunks = []

            for index, document in enumerate(documents, start=1):
                chunks.append(
                    DocumentChunk(
                        text=document.text,
                        metadata={
                            **document.metadata,
                            "chunk_index": index,
                        },
                    )
                )

            return chunks

    return FakeChunker()

@pytest.fixture
def fake_vector_store():
    class FakeVectorStore:
        def __init__(self):
            self.documents = {}

        def replace_document(self, source, chunks):
            self.documents[source] = chunks

    return FakeVectorStore()

def test_ingestion_processes_all_documents(
    fake_repository,
    fake_loader,
    fake_chunker,
    fake_vector_store,
):
    ingestion = Ingestion(
        repository=fake_repository,
        loader=fake_loader,
        chunker=fake_chunker,
        vector_store=fake_vector_store,
    )

    report = ingestion.run()

    assert report.total_documents == 2
    assert report.processed_documents == 2
    assert report.failed_documents == 0
    assert report.total_chunks == 2
    assert report.errors == []

    assert len(fake_vector_store.documents) == 2
    
def test_ingestion_continues_when_document_fails(
    fake_repository,
    fake_loader,
    fake_chunker,
    fake_vector_store,
):
    class FailingLoader:
        def load(self, content, filename, document_type):
            if "certificado" in filename:
                raise ValueError("Erro simulado na leitura")

            return fake_loader.load(content, filename, document_type)

    ingestion = Ingestion(
        repository=fake_repository,
        loader=FailingLoader(),
        chunker=fake_chunker,
        vector_store=fake_vector_store,
    )

    report = ingestion.run()

    assert report.total_documents == 2
    assert report.processed_documents == 1
    assert report.failed_documents == 1
    assert report.total_chunks == 1

    assert len(report.errors) == 1
    assert "certificado" in report.errors[0]

    assert len(fake_vector_store.documents) == 1

def test_ingestion_fails_when_document_generates_no_chunks(
    fake_repository,
    fake_loader,
    fake_chunker,
    fake_vector_store,
):
    class EmptyChunker:
        def chunk_documents(self, documents):
            return []

    ingestion = Ingestion(
        repository=fake_repository,
        loader=fake_loader,
        chunker=EmptyChunker(),
        vector_store=fake_vector_store,
    )

    report = ingestion.run()

    assert report.total_documents == 2
    assert report.processed_documents == 0
    assert report.failed_documents == 2
    assert report.total_chunks == 0

    assert len(report.errors) == 2
    assert len(fake_vector_store.documents) == 0

def test_ingestion_preserves_previous_chunks_when_replacement_fails(
    fake_repository,
    fake_loader,
    fake_chunker,
    fake_vector_store,
):
    previous_chunks = [
        DocumentChunk(
            text="Conteúdo antigo",
            metadata={
                "source": "certificacoes/certificado.pdf",
                "chunk_index": 1,
            },
        )
    ]

    fake_vector_store.documents[
        "certificacoes/certificado.pdf"
    ] = previous_chunks

    class FailingVectorStore:
        def __init__(self):
            self.documents = fake_vector_store.documents

        def replace_document(self, source, chunks):
            if source == "certificacoes/certificado.pdf":
                raise RuntimeError("Falha simulada na substituição")

            self.documents[source] = chunks

    vector_store = FailingVectorStore()

    ingestion = Ingestion(
        repository=fake_repository,
        loader=fake_loader,
        chunker=fake_chunker,
        vector_store=vector_store,
    )

    report = ingestion.run()

    assert report.processed_documents == 1
    assert report.failed_documents == 1

    assert (
        vector_store.documents["certificacoes/certificado.pdf"]
        == previous_chunks
    )

    assert "contratos/contrato.pdf" in vector_store.documents
    