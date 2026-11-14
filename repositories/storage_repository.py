"""Leitura genérica de CSV e JSON.

Função:
    Base compartilhada pelos repositórios de dados estruturados.

Responsabilidades:
    - Ler CSV e JSON a partir do Storage (encoding, separador, parsing)
    - Evitar código duplicado nos demais repositórios

Não deve:
    - Conhecer o significado dos dados de cada arquivo

Relações:
    Usa:        storage (get_storage)
    Usado por:  demais repositórios

Observação:
    Não confundir com a pasta storage/: aqui está o parsing, lá estão os backends de armazenamento.

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
