"""Schemas de relatórios e notificações.

Função:
    Representa o resumo individual de um produtor e a notificação a ser redigida.

Responsabilidades:
    - Relatório: vendas do período, pedidos alocados e pendências financeiras
    - Notificação: produtor destinatário, pedido relacionado e dados para o texto

Não deve:
    - Enviar mensagens (o sistema só redige o texto)

Relações:
    Usa:        pydantic
    Usado por:  services.relatorio_service, services.produtor_service

Status: esqueleto. Será implementado na Fase 6 (Agente de Produtores, relatórios e notificações).
"""
