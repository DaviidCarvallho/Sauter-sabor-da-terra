"""Serviço de produtores.

Função:
    Reúne cadastro, pedidos e financeiro de um produtor.

Responsabilidades:
    - Consultar produtores e seus produtos
    - Consultar pedidos alocados a um produtor
    - Consultar vendas e pendências financeiras

Não deve:
    - Redigir texto final (função do agente)

Relações:
    Usa:        repositories.produtor_repository, repositories.pedido_repository, repositories.financeiro_repository
    Usado por:  services.relatorio_service, agents.tools, api.produtores_controller

Status: esqueleto. Será implementado na Fase 6 (Agente de Produtores, relatórios e notificações).
"""
