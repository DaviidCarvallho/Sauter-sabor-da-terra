"""Schemas de pedidos.

Função:
    Representa um pedido bruto (texto livre) e o pedido estruturado após a triagem.

Responsabilidades:
    - Pedido estruturado: itens (produto, quantidade, unidade), prazo, comprador, tipo e urgência
    - Informações ausentes ou ambíguas e alertas (fora de safra, quantidade acima da capacidade)

Não deve:
    - Inventar valores para 'tipo' ou 'urgência' antes de analisar o pedidos.json

Relações:
    Usa:        pydantic
    Usado por:  services.pedido_service, repositories.pedido_repository, agents.tools

Observação:
    Os campos seguem o item 4.1 do enunciado. Os valores possíveis de tipo e urgência serão definidos a partir dos dados reais.

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
