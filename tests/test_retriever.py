
import pytest
from unittest.mock import Mock

from rag.chunker import DocumentChunk
from rag.retriever import RetrievedChunk, Retriever


@pytest.fixture
def sample_chunks():
    return [
        (
            DocumentChunk(
                text="A cooperativa produz queijo artesanal.",
                metadata={
                    "source": "queijo.txt",
                    "document_type": "ficha_tecnica",
                    "page": 1,
                    "chunk_index": 0,
                },
            ),
            0.15,
        ),
        (
            DocumentChunk(
                text="O leite é utilizado na produção de queijos.",
                metadata={
                    "source": "leite.txt",
                    "document_type": "ficha_tecnica",
                    "page": 2,
                    "chunk_index": 0,
                },
            ),
            0.42,
        ),
    ]


@pytest.fixture
def vector_store(sample_chunks):
    store = Mock()
    store.search.return_value = sample_chunks
    return store


@pytest.fixture
def retriever(vector_store):
    return Retriever(vector_store)


def test_retrieve(retriever, vector_store):
    results = retriever.retrieve("Produção de queijo")

    assert len(results) == 2
    assert all(isinstance(item, RetrievedChunk) for item in results)
    vector_store.search.assert_called_once_with(
        query="Produção de queijo",
        n_results=5,
    )


def test_retrieve_com_top_k(retriever, vector_store):
    retriever.retrieve("Produção de queijo", top_k=3)

    vector_store.search.assert_called_once_with(
        query="Produção de queijo",
        n_results=3,
    )


def test_retrieve_com_threshold(retriever):
    results = retriever.retrieve(
        "Produção de queijo",
        max_distance=0.30,
    )

    assert len(results) == 1
    assert results[0].distance == 0.15


def test_retrieve_sem_threshold(retriever):
    results = retriever.retrieve("Produção de queijo")

    assert len(results) == 2


def test_retrieve_consulta_vazia(retriever, vector_store):
    with pytest.raises(ValueError):
        retriever.retrieve("   ")

    vector_store.search.assert_not_called()


def test_retrieve_top_k_invalido(retriever, vector_store):
    with pytest.raises(ValueError):
        retriever.retrieve("Queijo", top_k=0)

    vector_store.search.assert_not_called()


def test_retrieve_threshold_negativo(retriever, vector_store):
    with pytest.raises(ValueError):
        retriever.retrieve("Queijo", max_distance=-0.1)

    vector_store.search.assert_not_called()


def test_retrieve_sem_resultados(retriever, vector_store):
    vector_store.search.return_value = []

    results = retriever.retrieve("Produto inexistente")

    assert results == []


def test_retrieve_preserva_metadados(retriever, sample_chunks):
    results = retriever.retrieve("Produção de queijo")

    assert results[0].chunk.metadata == sample_chunks[0][0].metadata
    assert results[0].chunk.metadata["source"] == "queijo.txt"
    assert results[0].chunk.metadata["page"] == 1
