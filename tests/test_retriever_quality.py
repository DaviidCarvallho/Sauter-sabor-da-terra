
"""Testes de qualidade da recuperação com documentos reais.

Execução:
    $env:RUN_RETRIEVER_QUALITY="1"
    pytest tests/test_retriever_quality.py -v
"""

import os

import pytest

from rag.retriever import Retriever
from rag.vector_store import VectorStore


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_RETRIEVER_QUALITY") != "1",
    reason="Testes de qualidade exigem execução explícita.",
)


@pytest.fixture(scope="module")
def retriever():
    return Retriever(VectorStore())


@pytest.mark.parametrize(
    ("query", "expected_source"),
    [
        (
            "Qual é a validade da certificação orgânica "
            "da produtora Ana Lúcia Bezerra da Costa?",
            "certificacoes/cert_organica_ana_bezerra_P004.txt",
        ),
        (
            "Quais produtos e volumes semanais estão previstos "
            "no contrato com o Mercado Bom Preço?",
            "contratos/contrato_mercado_bom_preco.txt",
        ),
        (
            "Quais são os preços da alface, rúcula e espinafre "
            "comercializados pela cooperativa?",
            "fichas_tecnicas/hortalicas.txt",
        ),
        (
            "Quais produtos são fornecidos pela produtora "
            "Ana Lúcia Bezerra?",
            "fichas_tecnicas/hortalicas.txt",
        ),
    ],
)
def test_retriever_finds_expected_source(
    retriever,
    query,
    expected_source,
):
    results = retriever.retrieve(query=query, top_k=5)

    sources = [
        result.metadata.get("source")
        for result in results
    ]

    assert expected_source in sources


def test_retriever_filters_query_without_evidence(retriever):
    results = retriever.retrieve(
        query="Qual foi o faturamento da cooperativa em 2019?",
        top_k=5,
        max_distance=0.30,
    )

    assert results == []


def test_retriever_preserves_relevant_result_with_threshold(retriever):
    results = retriever.retrieve(
        query=(
            "Quais são os preços da alface, rúcula e espinafre "
            "comercializados pela cooperativa?"
        ),
        top_k=5,
        max_distance=0.30,
    )

    sources = [
        result.metadata.get("source")
        for result in results
    ]

    assert "fichas_tecnicas/hortalicas.txt" in sources
