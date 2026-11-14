"""Schemas de produtos, sazonalidade, preços e lotes.

Função:
    Representa o catálogo de produtos e a rastreabilidade de lotes.

Responsabilidades:
    - Disponibilidade por mês (sazonalidade.csv)
    - Preço convencional e orgânico (tabela_precos_outubro_2026.csv)
    - Lote entregue e sua origem (lotes.csv)

Não deve:
    - Fixar campos antes de conhecer os arquivos

Relações:
    Usa:        pydantic
    Usado por:  repositories.produto_repository, repositories.lote_repository, services.pedido_service, services.documento_service

Observação:
    Arquivo adicionado à estrutura original: sazonalidade, preços e lotes não tinham modelo.

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
