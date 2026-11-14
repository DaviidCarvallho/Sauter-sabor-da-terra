"""Schemas de produtores e financeiro.

Função:
    Representa o cadastro dos produtores e suas transações financeiras.

Responsabilidades:
    - Produtor: identificação, município, produtos e certificações
    - Transação financeira: vendas e pagamentos (set-out/2026)

Não deve:
    - Fixar campos antes de conhecer produtores.csv e financeiro.csv

Relações:
    Usa:        pydantic
    Usado por:  repositories.produtor_repository, repositories.financeiro_repository, services.produtor_service

Observação:
    Os campos serão definidos a partir das colunas reais dos arquivos.

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
