"""Serviço de chat.

Função:
    Liga a API ao agente: executa o orquestrador do ADK mantendo a sessão do usuário.

Responsabilidades:
    - Criar ou recuperar a sessão (contexto da conversa), isolada por usuário
    - Executar o Runner do ADK com o agente raiz
    - Extrair a resposta final e a lista de agentes acionados
    - Traduzir falhas em exceções tipadas (sem expor detalhes internos)

Não deve:
    - Conhecer HTTP/FastAPI
    - Conter regra de negócio da cooperativa

Relações:
    Usa:        agents.agent (root_agent), models.chat_model, utils.config
    Usado por:  api.chat_controller

Observações:
    - Também exporta GOOGLE_API_KEY para o ambiente, pois o ADK a lê de os.environ.
    - Os imports do ADK são tardios para o servidor subir (health, frontend) mesmo sem o extra "ai".
    - Sessões em memória: reiniciar o servidor apaga o contexto (limitação conhecida). Um session_id
      desconhecido (ou de outro usuário) gera uma sessão nova, devolvida na resposta.
    - Não registra o conteúdo das mensagens nos logs.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from models.chat_model import ChatRequest, ChatResponse, FonteDocumental
from utils.config import get_settings
from utils.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from google.adk.agents import BaseAgent
    from google.adk.sessions import BaseSessionService

logger = get_logger(__name__)

APP_NAME = "sabor_da_terra"
CHAVE_FONTES = "fontes_documentais"  # preenchida por agents.tools.consultar_documentos


class ChatIndisponivelError(RuntimeError):
    """IA não configurada ou dependências ausentes no servidor."""


class ChatLimiteError(RuntimeError):
    """Cota/limite de requisições da API de IA atingido (429): transitório, vale tentar de novo."""


class ChatFalhaError(RuntimeError):
    """Falha ao executar o agente (modelo indisponível, erro inesperado, resposta vazia)."""


def _credencial_invalida(exc: Exception) -> bool:
    """True quando a API do Gemini recusou a chave (400 API_KEY_INVALID, 401 ou 403)."""
    try:
        from google.genai import errors
    except ImportError:  # pragma: no cover
        return False
    if not isinstance(exc, errors.ClientError):
        return False
    return exc.code in (401, 403) or "API_KEY_INVALID" in str(exc)


def _limite_excedido(exc: Exception) -> bool:
    """True para 429 RESOURCE_EXHAUSTED (o ADK pode embrulhar o erro em outra classe)."""
    return "RESOURCE_EXHAUSTED" in str(exc) or "ResourceExhausted" in type(exc).__name__


class ChatService:
    def __init__(
        self,
        agente: BaseAgent | None = None,
        session_service: BaseSessionService | None = None,
    ) -> None:
        self._agente = agente
        self._sessions = session_service
        self._runner: Any = None

    # -- montagem tardia ----------------------------------------------------

    def _preparar(self) -> None:
        if self._runner is not None:
            return
        settings = get_settings()
        if self._agente is None:
            if settings.google_api_key is None:
                raise ChatIndisponivelError("GOOGLE_API_KEY não configurada.")
            os.environ.setdefault("GOOGLE_API_KEY", settings.google_api_key.get_secret_value())
            try:
                from agents.agent import root_agent
            except ImportError as exc:
                raise ChatIndisponivelError("Dependências de IA ausentes (pip install -e '.[ai]').") from exc
            self._agente = root_agent
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
        except ImportError as exc:
            raise ChatIndisponivelError("Dependências de IA ausentes (pip install -e '.[ai]').") from exc
        self._sessions = self._sessions or InMemorySessionService()
        self._runner = Runner(app_name=APP_NAME, agent=self._agente, session_service=self._sessions)

    async def _obter_sessao(self, user_id: str, session_id: str | None):
        if session_id:
            existente = await self._sessions.get_session(
                app_name=APP_NAME, user_id=user_id, session_id=session_id
            )
            if existente is not None:
                return existente
            logger.info("Sessão desconhecida; criando uma nova.")
        return await self._sessions.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=uuid4().hex
        )

    # -- caso de uso --------------------------------------------------------

    async def responder(self, req: ChatRequest) -> ChatResponse:
        self._preparar()
        from google.genai import types

        sessao = await self._obter_sessao(req.user_id, req.session_id)
        conteudo = types.Content(role="user", parts=[types.Part(text=req.message)])

        especialistas = {t.name for t in getattr(self._agente, "tools", []) if hasattr(t, "agent")}
        resposta, usados = "", []
        try:
            # O estado das fontes é zerado a cada turno; o Agente de Documentos o preenche.
            async for evento in self._runner.run_async(
                user_id=req.user_id,
                session_id=sessao.id,
                new_message=conteudo,
                state_delta={CHAVE_FONTES: []},
            ):
                for chamada in evento.get_function_calls() or []:
                    if chamada.name in especialistas and chamada.name not in usados:
                        usados.append(chamada.name)
                if evento.is_final_response() and evento.content and evento.content.parts:
                    resposta = "".join(p.text or "" for p in evento.content.parts).strip()
        except Exception as exc:  # fronteira do serviço: registra o tipo (sem conteúdo) e tipifica
            if _credencial_invalida(exc):
                # Erro de configuração do servidor, não falha transitória: vira 503 na API.
                logger.error("Credencial de IA recusada pela API (chave inválida ou sem permissão).")
                raise ChatIndisponivelError("Credencial de IA inválida.") from exc
            if _limite_excedido(exc):
                logger.warning("Limite de requisições da API de IA atingido (429).")
                raise ChatLimiteError("Limite de requisições da IA atingido.") from exc
            logger.error("Falha ao executar o agente (%s)", type(exc).__name__)
            raise ChatFalhaError("Falha ao executar o assistente.") from exc

        if not resposta:
            logger.error("O agente terminou sem resposta final.")
            raise ChatFalhaError("O assistente não produziu resposta.")

        fontes = await self._fontes_da_sessao(req.user_id, sessao.id)
        logger.info("Chat respondido (sessão %s…, agentes=%s, fontes=%d)", sessao.id[:8], usados, len(fontes))
        return ChatResponse(answer=resposta, session_id=sessao.id, agents_used=usados, sources=fontes)

    async def _fontes_da_sessao(self, user_id: str, session_id: str) -> list[FonteDocumental]:
        sessao = await self._sessions.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        brutas = (sessao.state.get(CHAVE_FONTES) if sessao else None) or []
        return [FonteDocumental(**f) for f in brutas if isinstance(f, dict) and f.get("source")]


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService()
