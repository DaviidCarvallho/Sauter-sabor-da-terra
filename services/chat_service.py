"""Serviço de chat.

Função:
    Liga a API ao agente: executa o orquestrador do ADK mantendo a sessão do usuário.

Responsabilidades:
    - Criar ou recuperar a sessão (contexto da conversa)
    - Executar o Runner do ADK com o agente raiz
    - Extrair a resposta final e a lista de agentes acionados

Não deve:
    - Conhecer HTTP/FastAPI
    - Conter regra de negócio da cooperativa

Relações:
    Usa:        agents.agent (root_agent), models.chat_model, utils.config
    Usado por:  api.chat_controller

Observação:
    Também exportará GOOGLE_API_KEY para o ambiente, pois o ADK a lê de os.environ.

Status: esqueleto. Será implementado na Fase 4 (orquestrador, Agente de Pedidos e API de chat).
"""
