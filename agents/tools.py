"""Ferramentas dos agentes.

Função:
    Funções Python tipadas e com docstring que o ADK expõe ao modelo.

Responsabilidades:
    - Organizadas por especialista (pedidos, documentos, produtores)
    - Cada ferramenta é fina: chama um serviço e devolve um dicionário simples

Não deve:
    - Ler arquivos, CSV ou ChromaDB diretamente
    - Conter regra de negócio

Relações:
    Usa:        services.*
    Usado por:  agents.subagents.*

Observação:
    A docstring de cada ferramenta é o que o modelo lê para decidir quando usá-la.

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
