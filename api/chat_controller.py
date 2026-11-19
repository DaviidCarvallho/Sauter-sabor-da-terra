"""Rota do chat.

Função:
    Expõe POST /api/chat, a porta de entrada da conversa com o assistente.

Responsabilidades:
    - Validar o corpo da requisição (ChatRequest)
    - Delegar o processamento ao chat_service
    - Devolver ChatResponse e traduzir falhas em respostas HTTP (sem detalhes internos)

Não deve:
    - Instanciar ou conhecer agentes do ADK
    - Conter regra de negócio

Relações:
    Usa:        models.chat_model, services.chat_service
    Usado por:  main.py (registro do router)

Erros: 422 (corpo inválido, pelo FastAPI), 503 (IA não configurada), 502 (falha do assistente).
Formato: {"detail": "mensagem"}, que o frontend já interpreta.
"""

from fastapi import APIRouter, Depends, HTTPException

from models.chat_model import ChatRequest, ChatResponse
from services.chat_service import ChatFalhaError, ChatIndisponivelError, ChatService, get_chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, service: ChatService = Depends(get_chat_service)) -> ChatResponse:
    """Envia uma mensagem ao assistente e devolve a resposta, a sessão e os agentes acionados."""
    try:
        return await service.responder(req)
    except ChatIndisponivelError as exc:
        raise HTTPException(
            status_code=503, detail="O assistente de IA não está configurado no servidor."
        ) from exc
    except ChatFalhaError as exc:
        raise HTTPException(
            status_code=502, detail="Não foi possível obter uma resposta agora. Tente novamente."
        ) from exc
