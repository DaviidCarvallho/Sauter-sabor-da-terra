"""Repositório de documentos.

Função:
    Acesso aos arquivos das pastas certificacoes/, contratos/ e fichas_tecnicas/.

Responsabilidades:
    - Listar documentos e entregar seus bytes
    - Informar o tipo do documento a partir da pasta de origem

Não deve:
    - Extrair texto (função do rag.document_loader)

Relações:
    Usa:        storage (get_storage)
    Usado por:  rag.ingestion, services.documento_service

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
