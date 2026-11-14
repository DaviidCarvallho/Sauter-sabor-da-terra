"""Repositório de produtos.

Função:
    Acesso a sazonalidade.csv e tabela_precos_outubro_2026.csv.

Responsabilidades:
    - Consultar disponibilidade por mês e preços (convencional e orgânico)

Não deve:
    - Decidir se um pedido é viável (função do pedido_service)

Relações:
    Usa:        repositories.storage_repository, models.produto_model
    Usado por:  services.pedido_service

Observação:
    Arquivo adicionado à estrutura original: sazonalidade e preços não tinham repositório.

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
