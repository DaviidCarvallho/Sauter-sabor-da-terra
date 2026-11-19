"""Rotas REST de pedidos (opcional).

Função:
    Consulta e triagem de pedidos por HTTP, para a interface ou depuração.

Responsabilidades:
    - Listar pedidos e acionar a triagem de um pedido específico (rotas a confirmar)

Não deve:
    - Ser usado pelos agentes (eles chamam os serviços diretamente)
    - Conter regra de negócio

Relações:
    Usa:        models.pedido_model, services.pedido_service
    Usado por:  main.py (se for ativado)

Observação:
    Só será ativado se a interface precisar. O fluxo principal passa por /api/chat.

Status: esqueleto, opcional. A triagem já funciona pelo chat (Agente de Pedidos);
esta rota só será criada se a interface precisar de triagem direta.
"""
