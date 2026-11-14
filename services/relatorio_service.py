"""Serviço de relatórios.

Função:
    Monta os dados do resumo individual e da notificação de um produtor.

Responsabilidades:
    - Calcular vendas do período, pedidos alocados e pendências
    - Entregar dados estruturados para o agente redigir o texto

Não deve:
    - Enviar a notificação
    - Acessar arquivos diretamente

Relações:
    Usa:        services.produtor_service, models.relatorio_model
    Usado por:  agents.tools, api.produtores_controller

Status: esqueleto. Será implementado na Fase 6 (Agente de Produtores, relatórios e notificações).
"""
