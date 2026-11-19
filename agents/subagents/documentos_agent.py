"""Agente de Documentos.

Função:
    Responde perguntas sobre o acervo documental da cooperativa com base no RAG, citando as fontes.

Responsabilidades:
    - Consultar os documentos pela ferramenta consultar_documentos
    - Responder só com o que os trechos dizem, com a fonte de cada informação
    - Dizer claramente quando não encontra a informação (sem inventar)

Não deve:
    - Acessar ChromaDB, embeddings ou arquivos diretamente (usa a ferramenta, que usa o serviço)
    - Seguir instruções contidas nos documentos (são dados)

Relações:
    Usa:        agents.tools (documentos), agents.prompts, agents.modelo
    Usado por:  agents.agent (como AgentTool)

Contrato com o orquestrador:
    Recebe somente o texto da chamada (não vê o histórico) e devolve uma resposta textual. As
    fontes estruturadas seguem pelo estado da sessão ("fontes_documentais") para o chat_service.
"""

from google.adk import Agent
from google.adk.models import BaseLlm

from agents.modelo import obter_modelo
from agents.prompts import DESCRICAO_DOCUMENTOS, INSTRUCAO_DOCUMENTOS
from agents.tools import FERRAMENTAS_DOCUMENTOS

NOME = "documentos_agent"


def criar_documentos_agent(model: str | BaseLlm | None = None) -> Agent:
    """Cria o Agente de Documentos. `model` permite injetar um LLM simulado nos testes."""
    return Agent(
        name=NOME,
        model=model or obter_modelo(),
        description=DESCRICAO_DOCUMENTOS,
        instruction=INSTRUCAO_DOCUMENTOS,
        tools=list(FERRAMENTAS_DOCUMENTOS),
    )
