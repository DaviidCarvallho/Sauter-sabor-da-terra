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

Status: esqueleto, opcional. A consulta documental já funciona pelo chat (Agente de Documentos);
esta rota só será criada se a interface precisar de consulta direta ou reindexação.
"""
