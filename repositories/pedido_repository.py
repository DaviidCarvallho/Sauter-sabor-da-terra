"""Repositório de pedidos.

Função:
    Acesso a pedidos.json (somente leitura na primeira versão).

Responsabilidades:
    - Listar pedidos e buscar por identificador ou produtor

Não deve:
    - Gravar no JSON (decisão pendente sobre persistir pedidos processados)

Relações:
    Usa:        repositories.storage_repository, models.pedido_model
    Usado por:  services.pedido_service, services.produtor_service

Status: esqueleto. Será implementado na Fase 3 (dados e repositórios).
"""
