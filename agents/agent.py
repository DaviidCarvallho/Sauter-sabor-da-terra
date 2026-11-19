"""Agente principal (orquestrador).

Função:
    Interpreta a solicitação e a delega ao especialista adequado, combinando respostas quando preciso.

Responsabilidades:
    - Definir o root_agent exigido pelo ADK (e pelo comando `adk web`)
    - Registrar os especialistas como AgentTool
    - Decidir o roteamento a partir das descrições e instruções

Não deve:
    - Acessar dados ou arquivos
    - Conhecer HTTP

Relações:
    Usa:        agents.subagents.*, agents.prompts, agents.modelo
    Usado por:  services.chat_service

Decisão:
    AgentTool em vez de sub_agents (contrato da equipe): o orquestrador continua no comando, o
    especialista recebe só o texto da chamada e perguntas que cruzam especialistas são combinadas aqui.

Contrato de plug-in dos especialistas:
    Cada módulo em agents/subagents expõe `criar_<nome>_agent(model=None) -> Agent`
    (ex.: criar_documentos_agent, criar_produtores_agent). O orquestrador registra os que existirem
    e o prompt informa quais estão disponíveis, sem inventar capacidades dos ausentes.
"""

from __future__ import annotations

import importlib
from typing import Any

from google.adk import Agent
from google.adk.models import BaseLlm
from google.adk.tools import AgentTool

from agents.modelo import obter_modelo
from agents.prompts import instrucao_orquestrador
from utils.logger import get_logger

logger = get_logger(__name__)

ESPECIALISTAS: tuple[tuple[str, str], ...] = (
    ("agents.subagents.pedidos_agent", "criar_pedidos_agent"),
    ("agents.subagents.documentos_agent", "criar_documentos_agent"),
    ("agents.subagents.produtores_agent", "criar_produtores_agent"),
)


def _criar_especialistas(model: str | BaseLlm) -> list[Agent]:
    criados: list[Agent] = []
    for modulo, fabrica in ESPECIALISTAS:
        try:
            funcao = getattr(importlib.import_module(modulo), fabrica)
        except AttributeError:
            logger.warning("Especialista ainda não implementado: %s.%s", modulo, fabrica)
            continue
        criados.append(funcao(model))
    return criados


def construir_root_agent(model: str | BaseLlm | None = None) -> Agent:
    """Monta o orquestrador com os especialistas disponíveis."""
    modelo: Any = model or obter_modelo()
    especialistas = _criar_especialistas(modelo)
    return Agent(
        name="assistente_sabor_da_terra",
        model=modelo,
        description="Orquestrador do assistente da Cooperativa Sabor da Terra.",
        instruction=instrucao_orquestrador({a.name: a.description for a in especialistas}),
        tools=[AgentTool(agent=a) for a in especialistas],
    )


root_agent = construir_root_agent()
