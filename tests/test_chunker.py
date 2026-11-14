
import pytest

from rag.document_loader import LoadedDocument
from rag.chunker import TextChunker


def criar_documento(texto, metadata=None):
    return LoadedDocument(
        text=texto,
        metadata=metadata or {
            "source": "teste.txt",
            "document_type": "certificacao",
            "page": 1,
        },
    )


def test_documento_vazio():
    chunker = TextChunker()
    documento = criar_documento("   ")

    chunks = chunker.chunk_documents([documento])

    assert chunks == []


def test_documento_menor_que_chunk_size():
    chunker = TextChunker()
    documento = criar_documento("Texto pequeno para teste.")

    chunks = chunker.chunk_documents([documento])

    assert len(chunks) == 1
    assert chunks[0].text == "Texto pequeno para teste."


def test_documento_exatamente_com_chunk_size():
    chunker = TextChunker(chunk_size=1000, chunk_overlap=150)
    documento = criar_documento("A" * 1000)

    chunks = chunker.chunk_documents([documento])

    assert len(chunks) == 1
    assert len(chunks[0].text) == 1000


def test_overlap_entre_chunks():
    chunker = TextChunker(chunk_size=1000, chunk_overlap=150)

    texto = "A" * 2000
    documento = criar_documento(texto)

    chunks = chunker.chunk_documents([documento])

    assert len(chunks) > 1
    assert chunks[0].text[-150:] == chunks[1].text[:150]


def test_preservacao_dos_metadados():
    chunker = TextChunker(chunk_size=1000, chunk_overlap=150)

    metadata = {
        "source": "certificacao.txt",
        "document_type": "certificacao",
        "page": 2,
    }

    documento = criar_documento("A" * 1500, metadata)

    chunks = chunker.chunk_documents([documento])

    for chunk in chunks:
        assert chunk.metadata["source"] == "certificacao.txt"
        assert chunk.metadata["document_type"] == "certificacao"
        assert chunk.metadata["page"] == 2


def test_indices_sequenciais():
    chunker = TextChunker(chunk_size=1000, chunk_overlap=150)
    documento = criar_documento("A" * 2500)

    chunks = chunker.chunk_documents([documento])

    indices = [
        chunk.metadata["chunk_index"]
        for chunk in chunks
    ]

    assert indices == list(range(1, len(chunks) + 1))


def test_metadados_nao_sao_compartilhados():
    chunker = TextChunker(chunk_size=1000, chunk_overlap=150)
    documento = criar_documento("A" * 1500)

    chunks = chunker.chunk_documents([documento])

    chunks[0].metadata["source"] = "alterado.txt"

    assert chunks[1].metadata["source"] == "teste.txt"


def test_configuracao_invalida():
    with pytest.raises(ValueError):
        TextChunker(chunk_size=0)

    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, chunk_overlap=100)

    with pytest.raises(ValueError):
        TextChunker(chunk_size=100, chunk_overlap=-1)
