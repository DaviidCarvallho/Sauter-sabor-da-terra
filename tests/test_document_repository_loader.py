"""Testes do acesso aos documentos (DocumentRepository) e da extração de texto (DocumentLoader).

Usam os documentos reais de data/ e arquivos DOCX/PDF gerados em memória. Não usam ChromaDB nem a API.
"""

import io
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from rag.document_loader import DocumentLoader
from repositories.document_repository import DOCUMENT_CATEGORIES, DocumentRepository
from storage.local_storage import LocalStorage

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def repo():
    return DocumentRepository(LocalStorage(DATA))


# ---------- DocumentRepository ----------

def test_lista_os_documentos_reais_das_tres_categorias(repo):
    por_tipo: dict[str, int] = {}
    for doc in repo.list_documents():
        por_tipo[doc.document_type] = por_tipo.get(doc.document_type, 0) + 1
    # Enunciado: 12 certificações/laudos/inspeção, 3 contratos e 5 fichas técnicas.
    assert por_tipo == {"certificacao": 12, "contrato": 3, "ficha_tecnica": 5}


def test_chaves_sao_logicas_e_o_nome_e_o_arquivo(repo):
    docs = {d.key: d for d in repo.list_documents()}
    chave = "contratos/contrato_mercado_bom_preco.txt"
    assert chave in docs and docs[chave].name == "contrato_mercado_bom_preco.txt"
    assert not any(":" in k or "\\" in k for k in docs)  # nenhum caminho físico exposto


def test_le_bytes_e_identifica_o_tipo_pela_pasta(repo):
    chave = "certificacoes/inspecao_adagro_2026.txt"
    assert len(repo.get_document_bytes(chave)) > 0
    assert repo.get_document_type(chave) == "certificacao"
    assert repo.get_document_type("fichas_tecnicas/queijo_coalho.txt") == "ficha_tecnica"
    assert set(DOCUMENT_CATEGORIES.values()) == {"certificacao", "contrato", "ficha_tecnica"}


@pytest.mark.parametrize(
    "chave",
    ["../.env", "certificacoes/../../.env", "produtores.csv", "outra_pasta/x.txt", "contratos", "contratos//x.txt", ""],
)
def test_chaves_fora_das_categorias_ou_com_traversal_sao_recusadas(repo, chave):
    with pytest.raises(ValueError, match="inválida"):
        repo.get_document_bytes(chave)


def test_documento_inexistente_levanta_erro_de_leitura(repo):
    with pytest.raises(OSError):
        repo.get_document_bytes("contratos/nao_existe.txt")


# ---------- DocumentLoader ----------

def test_txt_real_preserva_origem_tipo_e_remove_bom():
    loader = DocumentLoader()
    docs = loader.load("﻿Cláusula 1: prazo de 12 meses.".encode("utf-8"), "contratos/x.txt", "contrato")
    assert docs[0].text == "Cláusula 1: prazo de 12 meses."  # sem o BOM
    assert docs[0].metadata["source"] == "contratos/x.txt" and docs[0].metadata["document_type"] == "contrato"


def test_loader_grava_page_1_para_txt_e_o_servico_de_documentos_nao_a_repassa():
    """Registro de comportamento: o loader marca page=1 em .txt. A omissão da página é feita no
    DocumentoService (contrato 5.4); ver tests/test_agents_documentos.py."""
    docs = DocumentLoader().load(b"texto", "a.txt", "contrato")
    assert docs[0].metadata["page"] == 1


def test_docx_extrai_paragrafos_sem_pagina():
    doc = Document()
    doc.add_paragraph("Certificação orgânica válida até 2026.")
    doc.add_paragraph("Produtor P004.")
    buf = io.BytesIO()
    doc.save(buf)
    docs = DocumentLoader().load(buf.getvalue(), "cert.docx", "certificacao")
    texto = " ".join(d.text for d in docs)
    assert "Certificação orgânica" in texto and "P004" in texto
    assert all(d.metadata["page"] is None for d in docs)


def test_pdf_sem_texto_nao_gera_trechos():
    escritor = PdfWriter()
    escritor.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    escritor.write(buf)
    assert DocumentLoader().load(buf.getvalue(), "vazio.pdf", "contrato") == []


@pytest.mark.parametrize(
    "conteudo, nome, erro",
    [
        (b"", "a.txt", ValueError),            # vazio
        ("texto", "a.txt", TypeError),         # str em vez de bytes
        (b"abc", "a.exe", ValueError),         # formato não suportado
        (b"abc", "semextensao", ValueError),
    ],
)
def test_entradas_invalidas_sao_recusadas(conteudo, nome, erro):
    with pytest.raises(erro):
        DocumentLoader().load(conteudo, nome, "contrato")


def test_todos_os_documentos_reais_sao_carregados_com_texto(repo):
    """Integração repositório + loader sobre o acervo real (base da ingestão)."""
    loader = DocumentLoader()
    for doc in repo.list_documents():
        trechos = loader.load(repo.get_document_bytes(doc.key), doc.key, doc.document_type)
        assert trechos and all(t.text.strip() for t in trechos), doc.key
        assert all(t.metadata["source"] == doc.key for t in trechos)
