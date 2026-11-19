"""Testes da consulta documental (RAG) do ponto de vista do usuário.

Casos previstos originalmente (Fase 5) e situação:
- Toda resposta cita o arquivo de origem ........... coberto abaixo (serviço) e em tests/test_agents_documentos.py
- Pergunta sem evidência retorna 'não encontrei' ... coberto abaixo (serviço) e em tests/test_agents_documentos.py
- Certificação orgânica vigente para mel é localizada na base ... exige índice real: ver o teste ignorado
- Rastreabilidade de um lote combina lotes.csv e documentos ..... não implementado: ver o teste ignorado

O RAG real (ChromaDB + embeddings) só roda com RUN_RETRIEVER_QUALITY=1 (tests/test_retriever_quality.py).
"""

import os

import pytest

from rag.retriever import RetrievedChunk
from services.documento_service import DocumentoService


class _RetrieverFalso:
    def __init__(self, chunks):
        self._chunks = chunks

    def retrieve(self, query, top_k=5, max_distance=None):
        return [c for c in self._chunks if max_distance is None or c.distance <= max_distance]


def _chunk(distancia, fonte="certificacoes/cert_organica_jose_santos_P002.txt"):
    return RetrievedChunk(
        id="c1", content="Mel silvestre. Validade: 2027-03-15.", distance=distancia, score=1 - distancia,
        metadata={"source": fonte, "document_type": "certificacao", "page": 1},
    )


def test_toda_resposta_documental_traz_o_arquivo_de_origem():
    r = DocumentoService(_RetrieverFalso([_chunk(0.1)])).consultar("certificação orgânica para mel")
    assert r.evidencia_suficiente
    assert r.fontes and all(f.source.endswith(".txt") for f in r.fontes)


def test_pergunta_sem_evidencia_nao_devolve_trechos_nem_fontes():
    r = DocumentoService(_RetrieverFalso([_chunk(0.9)])).consultar("qual o telefone do presidente?")
    assert not r.evidencia_suficiente and r.trechos == [] and r.fontes == []
    assert r.mensagem


@pytest.mark.skipif(os.getenv("RUN_RETRIEVER_QUALITY") != "1",
                    reason="Exige o índice vetorial real (python -m rag.ingestion) e a API de embeddings.")
def test_certificacao_organica_vigente_para_mel_e_localizada_na_base():
    r = DocumentoService().consultar("Quais produtores têm certificação orgânica para mel?")
    assert r.evidencia_suficiente
    assert any("mel" in t.content.lower() for t in r.trechos)


@pytest.mark.skip(reason="Pendente: rastreabilidade de lotes (lotes.csv + documentos) ainda não tem serviço nem ferramenta.")
def test_rastreabilidade_de_lote_combina_lotes_csv_e_documentos():
    ...
