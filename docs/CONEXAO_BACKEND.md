# Conectar o chat ao backend FastAPI (roteiro para quando estiver pronto)

O frontend já chama `POST /api/chat` e está testado contra um servidor simulado (`qa/mock_server.py`).
Este roteiro diz o que fazer quando o `chat_controller.py` for implementado (fase 4).

## 1. Combinar o contrato com Murilo e David (antes de tudo)

O `models/chat_model.py` (esqueleto) já prevê: `ChatRequest` com `user_id`, `session_id` (opcional) e `message`; `ChatResponse` com texto da resposta, `session_id` e agentes acionados. Faltam `sources` e `alerts`, que o frontend já exibe se vierem. O `main.py` serve `static/` na mesma origem, então não há CORS.


| Item | Frontend envia/espera hoje | Confirmar |
|---|---|---|
| Requisição | `{ "message": str, "session_id": str \| null, "user_id": str }` | nomes e obrigatoriedade |
| Resposta | `{ "reply", "session_id", "agents": [], "sources": [{"source","page"}], "alerts": [{"type","message","severity"}] }` | nomes e tipos |
| Erro | `{ "detail": "..." }` (padrão FastAPI) | formato |
| Tempo máximo | 60 s no navegador | se algum agente demora mais |
| Mensagem vazia | `message` com `maxlength` 4000 | limite no schema Pydantic |

O normalizador (`normalizarResposta` em `static/js/app.js`) já aceita `response`, `answer`, `resposta`,
`fontes`, `alertas`, `agentes`, `file`, `filename`, `pagina`, entre outros. Se o contrato final usar
outros nomes, ajuste só: `CONFIG` (rota), o corpo em `sendMessage()` e `normalizarResposta()`.

## 2. Subir o backend real

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```
Abra http://127.0.0.1:8000. O status no topo deve mostrar "Servidor online".

## 3. Rodar o verificador automático

```powershell
python qa\verificar_backend.py
```
Ele confere o contrato e os 4 cenários e salva `docs/evidencias/resultado_verificacao.md`
(anexe esse arquivo ao PR como evidência). Se o chat ainda for esqueleto, ele avisa e termina.

## 4. Conferência manual na interface (cenários de aceitação)

Use os botões de sugestão da tela inicial e marque em `docs/QA_CHECKLIST.md`:

1. **Triagem de pedido**: itens, quantidades, prazo e comprador; alertas de fora de safra / acima da capacidade.
2. **Consulta documental**: resposta com fontes (arquivo e página).
3. **Pergunta sem evidência**: o assistente diz que não encontrou, sem inventar.
4. **Relatório de produtor**: vendas, pedidos alocados e pendências.

Tire uma captura de cada cenário e salve em `docs/evidencias/`.

## 5. Testes do backend (tests/test_api.py)

Os testes do chat já estão em `tests/test_api.py` (os 5 testes originais foram mantidos). Eles são pulados
enquanto a rota não existir e passam a rodar sozinhos quando `/api/chat` for registrada em `main.py`.
Os que chamam o modelo exigem `GOOGLE_API_KEY` (`ai_configured` verdadeiro em `/api/health`). Rode `pytest`.

## 6. Sintomas comuns

| O que aparece na tela | Causa provável |
|---|---|
| "O servidor não encontrou a rota do chat" (404) | rota não registrada em `main.py` |
| "Essa função ainda não foi implementada" (501) | `chat_controller.py` ainda é esqueleto |
| "Mensagem não aceita: ..." (422) | nomes dos campos diferentes do schema Pydantic |
| "resposta em formato inesperado" | backend devolveu texto, não JSON |
| Resposta sem fontes/alertas | nomes de campo diferentes: ajustar `normalizarResposta()` |
| "Sem conexão com o servidor" | backend desligado ou CORS (se a página não for servida pelo próprio FastAPI) |
