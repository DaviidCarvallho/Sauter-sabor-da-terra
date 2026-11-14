"""Pipeline de ingestão.

Função:
    Constrói e reconstrói o índice vetorial a partir dos documentos da cooperativa.

Responsabilidades:
    - Listar documentos, carregar, dividir, gerar embeddings e gravar
    - Ser executável como comando (python -m rag.ingestion) e repetível

Não deve:
    - Rodar automaticamente a cada requisição do chat

Relações:
    Usa:        repositories.document_repository, rag.document_loader, rag.chunker, rag.vector_store
    Usado por:  Linha de comando; api.documentos_controller (se ativado)

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
