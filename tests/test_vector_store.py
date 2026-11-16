
import chromadb
import pytest

from rag.chunker import DocumentChunk
from rag.vector_store import VectorStore


@pytest.fixture
def vector_store(tmp_path, monkeypatch):
    """Cria um VectorStore isolado para cada teste."""

    store = VectorStore.__new__(VectorStore)

    store.client = chromadb.PersistentClient(
        path=str(tmp_path / "vectorstore")
    )

    store.collection = store.client.get_or_create_collection(
        name="test_collection",
        metadata={"hnsw:space": "cosine"},
    )

    store._embedding_client = None

    def fake_embeddings(texts, task_type):
        return [
            [1.0, 0.0, 0.0]
            for _ in texts
        ]

    monkeypatch.setattr(
        store,
        "_generate_embeddings",
        fake_embeddings,
    )

    return store


@pytest.fixture
def sample_chunks():
    return [
        DocumentChunk(
            text="A cooperativa produz queijo artesanal.",
            metadata={
                "source": "teste.txt",
                "document_type": "teste",
                "page": 1,
                "chunk_index": 0,
            },
        ),
        DocumentChunk(
            text="O leite é utilizado na produção de queijos.",
            metadata={
                "source": "teste.txt",
                "document_type": "teste",
                "page": 1,
                "chunk_index": 1,
            },
        ),
    ]


def test_add_chunks(vector_store, sample_chunks):
    vector_store.add_chunks(sample_chunks)

    assert vector_store.collection.count() == 2


def test_add_chunks_vazio(vector_store):
    vector_store.add_chunks([])

    assert vector_store.collection.count() == 0


def test_metadados_none(vector_store):
    metadata = vector_store._prepare_metadata({
        "source": "teste.docx",
        "page": None,
        "chunk_index": 0,
    })

    assert "page" not in metadata
    assert metadata["source"] == "teste.docx"


def test_search(vector_store, sample_chunks):
    vector_store.add_chunks(sample_chunks)

    results = vector_store.search(
        "Produção de queijo",
        n_results=2,
    )

    assert len(results) == 2
    assert all(isinstance(item, DocumentChunk) for item in results)


def test_search_sem_documentos(vector_store):
    results = vector_store.search("Produção de queijo")

    assert results == []


def test_search_consulta_vazia(vector_store):
    with pytest.raises(ValueError):
        vector_store.search("   ")


def test_delete_document(vector_store, sample_chunks):
    vector_store.add_chunks(sample_chunks)

    removed = vector_store.delete_document("teste.txt")

    assert removed == 2
    assert vector_store.collection.count() == 0


def test_delete_document_inexistente(vector_store):
    removed = vector_store.delete_document("inexistente.txt")

    assert removed == 0
