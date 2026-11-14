"""Recuperador.

Função:
    Busca os trechos mais relevantes para uma pergunta.

Responsabilidades:
    - Consultar o vector_store (top-k) e devolver trecho, fonte e score
    - Filtrar por metadados quando útil (tipo de documento, produtor)

Não deve:
    - Gerar a resposta final (função do agente)

Relações:
    Usa:        rag.vector_store, models.documento_model
    Usado por:  services.documento_service

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
