"""Serviço de pedidos.

Função:
    Validações determinísticas da triagem: o LLM interpreta o texto, o código confere os fatos.

Responsabilidades:
    - Conferir produto contra o catálogo e a sazonalidade (fora de safra)
    - Conferir quantidade contra a capacidade dos produtores
    - Classificar urgência e tipo conforme regras definidas a partir dos dados
    - Apontar informações ausentes, ambiguidades e inconsistências

Não deve:
    - Interpretar linguagem natural (função do agente)
    - Ler arquivos diretamente

Relações:
    Usa:        repositories.pedido_repository, repositories.produtor_repository, repositories.produto_repository
    Usado por:  agents.tools, api.pedidos_controller

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
