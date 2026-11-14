"""Serviço documental.

Função:
    Responde perguntas sobre o acervo com fontes e consulta a rastreabilidade de lotes.

Responsabilidades:
    - Buscar trechos relevantes via rag.retriever
    - Montar a resposta com as fontes ou informar que não há evidência suficiente
    - Consultar lotes.csv para perguntas de origem e rastreabilidade

Não deve:
    - Inventar informação ausente dos documentos
    - Conhecer detalhes do ChromaDB

Relações:
    Usa:        rag.retriever, repositories.lote_repository, repositories.document_repository
    Usado por:  agents.tools, api.documentos_controller

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
