"""Rota do chat.

Função:
    Expõe POST /api/chat, a porta de entrada da conversa com o assistente.

Responsabilidades:
    - Validar o corpo da requisição (ChatRequest)
    - Delegar o processamento ao chat_service
    - Devolver ChatResponse e traduzir falhas em respostas HTTP

Não deve:
    - Instanciar ou conhecer agentes do ADK
    - Conter regra de negócio

Relações:
    Usa:        models.chat_model, services.chat_service
    Usado por:  main.py (registro do router)

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
