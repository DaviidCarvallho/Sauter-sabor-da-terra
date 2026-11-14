"""Agente principal (orquestrador).

Função:
    Interpreta a solicitação e a delega ao especialista adequado, combinando respostas quando preciso.

Responsabilidades:
    - Definir o root_agent exigido pelo ADK (e pelo comando `adk web`)
    - Registrar os três especialistas como AgentTool
    - Decidir o roteamento a partir das descrições e instruções

Não deve:
    - Acessar dados ou arquivos
    - Conhecer HTTP

Relações:
    Usa:        agents.subagents.*, agents.prompts, utils.config
    Usado por:  services.chat_service

Observação:
    Decisão: AgentTool em vez de sub_agents, porque perguntas reais cruzam especialistas (ex.: disponibilidade e certificação de um produto).

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
