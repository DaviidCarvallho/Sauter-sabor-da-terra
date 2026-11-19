"""Agente de Pedidos.

Função:
    Interpreta pedidos em português coloquial e organiza a triagem.

Responsabilidades:
    - Extrair produtos, quantidades, prazos e comprador
    - Pedir ou sinalizar o que estiver ausente ou ambíguo
    - Usar as ferramentas de validação (safra, capacidade, urgência) e apresentar os resultados

Não deve:
    - Decidir sozinho fatos que o serviço pode verificar
    - Confirmar ou alocar pedidos

Relações:
    Usa:        agents.tools (pedidos), agents.prompts, agents.modelo
    Usado por:  agents.agent (como AgentTool)

Contrato com o orquestrador:
    Recebe somente o texto da chamada (não vê o histórico) e devolve uma resposta textual.
"""

from google.adk import Agent
from google.adk.models import BaseLlm

from agents.modelo import obter_modelo
from agents.prompts import DESCRICAO_PEDIDOS, INSTRUCAO_PEDIDOS
from agents.tools import FERRAMENTAS_PEDIDOS

NOME = "pedidos_agent"


def criar_pedidos_agent(model: str | BaseLlm | None = None) -> Agent:
    """Cria o Agente de Pedidos. `model` permite injetar um LLM simulado nos testes."""
    return Agent(
        name=NOME,
        model=model or obter_modelo(),
        description=DESCRICAO_PEDIDOS,
        instruction=INSTRUCAO_PEDIDOS,
        tools=list(FERRAMENTAS_PEDIDOS),
    )
