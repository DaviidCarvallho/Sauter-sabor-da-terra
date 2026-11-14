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
