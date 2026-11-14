"""Rotas REST de produtores (opcional).

Função:
    Consulta de produtores e de seus resumos por HTTP.

Responsabilidades:
    - Listar produtores e devolver o relatório individual (rotas a confirmar)

Não deve:
    - Conter regra de negócio

Relações:
    Usa:        models.produtor_model, models.relatorio_model, services.produtor_service, services.relatorio_service
    Usado por:  main.py (se for ativado)

Observação:
    Só será ativado se a interface precisar. O fluxo principal passa por /api/chat.

Status: esqueleto. Será implementado na Fase 6 (Agente de Produtores, relatórios e notificações).
"""
