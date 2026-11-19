"""LLM simulado para testar agentes do ADK sem chamar o Gemini.

O ScriptedLlm devolve, em ordem, respostas pré-definidas (texto ou chamada de ferramenta) e
guarda cada requisição recebida. As ferramentas, os serviços e o Runner do ADK são os reais:
só o modelo é simulado. Assim os testes verificam a trajetória (quem foi chamado, com quais
argumentos) e o uso correto dos resultados, sem custo e de forma determinística.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import Field


def texto(conteudo: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=conteudo)]))


def chamar(nome: str, **argumentos: Any) -> LlmResponse:
    parte = types.Part(function_call=types.FunctionCall(name=nome, args=argumentos))
    return LlmResponse(content=types.Content(role="model", parts=[parte]))


class ScriptedLlm(BaseLlm):
    model: str = "llm-simulado"
    respostas: list[Any] = Field(default_factory=list)
    requisicoes: list[Any] = Field(default_factory=list)

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"llm-simulado"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.requisicoes.append(llm_request)
        if not self.respostas:
            raise AssertionError("O roteiro do LLM simulado acabou: chamada inesperada ao modelo.")
        yield self.respostas.pop(0)


def instrucao_da_requisicao(req: LlmRequest) -> str:
    sistema = req.config.system_instruction if req.config else None
    return str(sistema or "")


def nomes_das_ferramentas(req: LlmRequest) -> list[str]:
    return sorted(req.tools_dict) if req.tools_dict else []


async def conversar(runner: Runner, user_id: str, session_id: str, mensagem: str):
    """Envia uma mensagem e devolve (texto_final, eventos)."""
    conteudo = types.Content(role="user", parts=[types.Part(text=mensagem)])
    eventos, final = [], ""
    async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=conteudo):
        eventos.append(ev)
        if ev.is_final_response() and ev.content and ev.content.parts:
            final = "".join(p.text or "" for p in ev.content.parts)
    return final, eventos


def chamadas_de_ferramenta(eventos) -> list[tuple[str, str, dict]]:
    """Lista (autor, nome, argumentos) de cada function_call, em ordem."""
    saida = []
    for ev in eventos:
        for c in ev.get_function_calls() or []:
            saida.append((ev.author, c.name, dict(c.args or {})))
    return saida


def respostas_de_ferramenta(eventos) -> dict[str, list[Any]]:
    saida: dict[str, list[Any]] = {}
    for ev in eventos:
        for r in ev.get_function_responses() or []:
            saida.setdefault(r.name, []).append(r.response)
    return saida


async def nova_sessao(app_name: str = "teste"):
    servico = InMemorySessionService()
    sessao = await servico.create_session(app_name=app_name, user_id="u1")
    return servico, sessao


def respostas_de_ferramenta_na_requisicao(req: LlmRequest) -> dict[str, list[Any]]:
    """function_response já presentes na requisição (resultado real das ferramentas do especialista)."""
    saida: dict[str, list[Any]] = {}
    for conteudo in req.contents or []:
        for parte in conteudo.parts or []:
            if parte.function_response is not None:
                saida.setdefault(parte.function_response.name, []).append(parte.function_response.response)
    return saida


def textos_do_usuario(req: LlmRequest) -> list[str]:
    return [
        p.text
        for c in req.contents or []
        if c.role == "user"
        for p in c.parts or []
        if p.text
    ]
