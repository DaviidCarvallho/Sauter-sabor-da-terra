"""Rotas REST de documentos (opcional).

Função:
    Consulta documental direta e reindexação da base por HTTP.

Responsabilidades:
    - Listar documentos indexados e disparar a ingestão (rotas a confirmar)

Não deve:
    - Conter lógica de RAG (pertence a rag/ e services/)

Relações:
    Usa:        models.documento_model, services.documento_service
    Usado por:  main.py (se for ativado)

Observação:
    Só será ativado se a interface precisar. O fluxo principal passa por /api/chat.

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
