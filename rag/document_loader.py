"""Carregador de documentos.

Função:
    Converte PDF e DOCX em texto com metadados.

Responsabilidades:
    - Receber os bytes do arquivo (vindos do document_repository)
    - Extrair texto e registrar arquivo, tipo de documento e página

Não deve:
    - Abrir arquivos pelo caminho físico

Relações:
    Usa:        repositories.document_repository, pypdf, python-docx
    Usado por:  rag.ingestion

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


@dataclass(frozen=True)
class LoadedDocument:
    """Representa o texto extraído de uma página ou unidade documental."""

    text: str
    metadata: dict


class DocumentLoader:
    """Extrai texto de documentos recebidos em bytes."""

    SUPPORTED_FORMATS = {".txt", ".pdf", ".docx"}

    def load(
        self,
        content: bytes,
        filename: str,
        document_type: str,
    ) -> list[LoadedDocument]:
        """Carrega um documento e retorna seu texto com metadados."""

        if not isinstance(content, bytes):
            raise TypeError("O conteúdo do documento deve ser bytes.")

        if not content:
            raise ValueError("O documento está vazio.")

        extension = Path(filename).suffix.lower()

        if extension not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Formato não suportado: {extension}"
            )

        if extension == ".txt":
            return self._load_txt(content, filename, document_type)

        if extension == ".pdf":
            return self._load_pdf(content, filename, document_type)

        return self._load_docx(content, filename, document_type)

    def _load_txt(
        self,
        content: bytes,
        filename: str,
        document_type: str,
    ) -> list[LoadedDocument]:
        """Extrai texto de um arquivo TXT."""

        text = content.decode("utf-8-sig")

        return [
            LoadedDocument(
                text=text,
                metadata={
                    "source": filename,
                    "document_type": document_type,
                    "page": 1,
                },
            )
        ]

    def _load_pdf(
        self,
        content: bytes,
        filename: str,
        document_type: str,
    ) -> list[LoadedDocument]:
        """Extrai texto página por página de um PDF."""

        reader = PdfReader(BytesIO(content))
        documents = []

        for page_number, page in enumerate(reader.pages, start=1):
            
            text = page.extract_text() or ""
            text = " ".join(text.split())
            
            if not text.strip():
                continue

            documents.append(
                LoadedDocument(
                    text=text,
                    metadata={
                        "source": filename,
                        "document_type": document_type,
                        "page": page_number,
                    },
                )
            )

        return documents

    def _load_docx(
        self,
        content: bytes,
        filename: str,
        document_type: str,
    ) -> list[LoadedDocument]:
        """Extrai texto de um arquivo DOCX."""

        document = Document(BytesIO(content))

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]

        tables = []
        for table in document.tables:
            for row in table.rows:
                cells = [
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                ]
                if cells:
                    tables.append(" | ".join(cells))

        text = "\n".join(paragraphs + tables)

        if not text.strip():
            return []

        return [
            LoadedDocument(
                text=text,
                metadata={
                    "source": filename,
                    "document_type": document_type,
                    "page": None,
                },
            )
        ]
