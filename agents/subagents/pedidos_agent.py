"""Agente de Pedidos.

Função:
    Interpreta pedidos em português coloquial e organiza a triagem.

Responsabilidades:
    - Extrair produtos, quantidades, prazos e comprador
    - Pedir ou sinalizar o que estiver ausente ou ambíguo
    - Usar as ferramentas de validação (sazonalidade, capacidade, urgência)

Não deve:
    - Decidir sozinho fatos que o serviço pode verificar

Relações:
    Usa:        agents.tools (pedidos), agents.prompts
    Usado por:  agents.agent

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
