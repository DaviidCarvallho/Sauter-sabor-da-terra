"""Agente de Produtores.

Função:
    Gera resumos individuais de produtores e redige rascunhos de notificação.

Responsabilidades:
    - Consultar cadastro, resumo financeiro e dados de notificação pelas ferramentas
    - Apresentar números exatamente como calculados pelos serviços (nada estimado pelo modelo)
    - Redigir notificações como rascunho (não envia mensagens)
    - Recusar consultas pessoais de quem escreve em nome próprio (o sistema não autentica)

Não deve:
    - Calcular valores, enviar mensagens ou alterar dados
    - Revelar CPF, telefone, endereço, conta bancária ou PIX

Relações:
    Usa:        agents.tools (produtores), agents.prompts, agents.modelo
    Usado por:  agents.agent (como AgentTool)

Contrato com o orquestrador:
    Recebe somente o texto da chamada (não vê o histórico) e devolve uma resposta textual.
"""

from google.adk import Agent
from google.adk.models import BaseLlm

from agents.modelo import obter_modelo
from agents.prompts import DESCRICAO_PRODUTORES, INSTRUCAO_PRODUTORES
from agents.tools import FERRAMENTAS_PRODUTORES

NOME = "produtores_agent"


def criar_produtores_agent(model: str | BaseLlm | None = None) -> Agent:
    """Cria o Agente de Produtores. `model` permite injetar um LLM simulado nos testes."""
    return Agent(
        name=NOME,
        model=model or obter_modelo(),
        description=DESCRICAO_PRODUTORES,
        instruction=INSTRUCAO_PRODUTORES,
        tools=list(FERRAMENTAS_PRODUTORES),
    )
