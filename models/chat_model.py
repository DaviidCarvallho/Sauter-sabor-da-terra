"""Schemas do chat.

Função:
    Define o contrato de entrada e saída da conversa.

Responsabilidades:
    - ChatRequest: user_id (alias "user"), session_id (opcional) e message
    - ChatResponse: answer, session_id, agents_used, sources, alerts e status

Não deve:
    - Conter lógica
    - Depender de agents/ ou de services/

Relações:
    Usa:        pydantic
    Usado por:  api.chat_controller, services.chat_service

Decisão de nomes (a confirmar com Murilo e Raquel):
    O PLANO_DE_TAREFAS (seção 9) e o frontend usam user_id e answer; o documento de contratos
    usa "user" e "message" apenas como exemplo ilustrativo. Adotamos user_id/answer e aceitamos
    "user" na entrada. O frontend já lê "answer", "reply", "response" e "message".
"""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Mensagem do usuário. `session_id` vazio inicia uma conversa nova."""

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    message: str = Field(min_length=1, max_length=4000, description="Texto enviado pelo usuário.")
    user_id: str = Field(
        default="anonimo",
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("user_id", "user"),
        description="Identificador do usuário; a sessão é isolada por usuário.",
    )
    session_id: str | None = Field(
        default=None, max_length=128, description="Sessão existente; vazio cria uma nova."
    )


class FonteDocumental(BaseModel):
    """Fonte de uma resposta documental (preenchida pelo Agente de Documentos)."""

    source: str
    page: int | None = None


class AlertaChat(BaseModel):
    """Alerta determinístico (calculado em código, não pelo LLM) para destaque na interface."""

    tipo: str
    severidade: str
    mensagem: str
    produto: str | None = None


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    agents_used: list[str] = Field(default_factory=list)
    sources: list[FonteDocumental] = Field(default_factory=list)
    alerts: list[AlertaChat] = Field(default_factory=list)
    status: Literal["success"] = "success"
