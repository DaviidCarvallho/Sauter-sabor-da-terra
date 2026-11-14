"""Schemas do chat.

Função:
    Define o contrato de entrada e saída da conversa.

Responsabilidades:
    - ChatRequest: user_id, session_id (opcional) e message
    - ChatResponse: texto da resposta, session_id e lista de agentes acionados (campos previstos)

Não deve:
    - Conter lógica
    - Depender de agents/ ou de services/

Relações:
    Usa:        pydantic
    Usado por:  api.chat_controller, services.chat_service

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
