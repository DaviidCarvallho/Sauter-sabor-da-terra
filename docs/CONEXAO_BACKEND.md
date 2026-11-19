# Conexão do chat com o backend FastAPI

O frontend chama `POST /api/chat`, que **já está implementado** (`api/chat_controller.py` → `services/chat_service.py` → `agents/`). Este documento descreve o contrato real, como verificar a conexão e os sintomas comuns. Antes do backend existir, a tela foi testada contra um servidor simulado (`qa/mock_server.py`), que continua útil para QA sem chave de API.

## 1. Contrato implementado

| Item | Requisição / resposta | Observação |
|---|---|---|
| Requisição | `{ "message": str (1 a 4000), "session_id": str \| null, "user_id": str }` | `user_id` aceita o alias `user`; `session_id` vazio inicia uma conversa |
| Resposta | `{ "answer", "session_id", "status", "agents_used": [], "sources": [{"source","page"}] }` | `sources` só vem preenchido pelo Agente de Documentos |
| Alertas | **não são enviados como campo** | A tela sabe exibir `alerts`, mas hoje os alertas da triagem vêm dentro do texto de `answer` |
| Erros | `{ "detail": "..." }` | 422 corpo inválido; 429 limite da IA (tentar de novo); 503 IA não configurada ou chave recusada; 502 falha do assistente |
| Tempo máximo | 60 s no navegador | Uma resposta com vários agentes pode levar 10 a 20 s; no Free Tier, mais |

`main.py` serve `static/` na mesma origem, então não há CORS. O normalizador (`normalizarResposta` em `static/js/app.js`) aceita nomes alternativos (`reply`, `response`, `agents`, `fontes`...), o que mantém o mock funcionando. Os nomes definitivos ainda dependem da confirmação do Murilo (ver `docs/CONTRATOS_ARQUITETURAIS.md`, seção 10.1).

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
(anexe esse arquivo ao PR como evidência). Os cenários B e D só fazem sentido com o índice de documentos construído e a chave de API configurada (cada cenário chama o modelo).

## 4. Conferência manual na interface (cenários de aceitação)

Use os botões de sugestão da tela inicial e marque em `docs/QA_CHECKLIST.md`:

1. **Triagem de pedido**: itens, quantidades, prazo e comprador; alertas de fora de safra / acima da capacidade.
2. **Consulta documental**: resposta com fontes (arquivo e página).
3. **Pergunta sem evidência**: o assistente diz que não encontrou, sem inventar.
4. **Relatório de produtor**: vendas, pedidos alocados e pendências.

Tire uma captura de cada cenário e salve em `docs/evidencias/`.

## 5. Testes do backend (tests/test_api.py)

Os testes do chat estão em `tests/test_api.py` e `tests/test_chat_integracao.py`. Os de integração usam um LLM simulado e não gastam cota. Os 2 testes de `test_api.py` que chamam o modelo exigem `GOOGLE_API_KEY` (`ai_configured` verdadeiro em `/api/health`) e **consomem a API**: para uma execução sem custo, use `$env:GOOGLE_API_KEY=""; pytest`.

## 6. Sintomas comuns

| O que aparece na tela | Causa provável |
|---|---|
| "O servidor não encontrou a rota do chat" (404) | servidor antigo em execução ou `main.py` sem o router de chat |
| "Muitas mensagens em pouco tempo" (429) | limite de requisições da API do Gemini (Free Tier); aguardar e tentar de novo |
| "O assistente de IA não está configurado" (503) | `GOOGLE_API_KEY` ausente ou recusada no `.env` |
| "Mensagem não aceita: ..." (422) | nomes dos campos diferentes do schema Pydantic |
| "resposta em formato inesperado" | backend devolveu texto, não JSON |
| Resposta sem fontes/alertas | nomes de campo diferentes: ajustar `normalizarResposta()` |
| "Sem conexão com o servidor" | backend desligado ou CORS (se a página não for servida pelo próprio FastAPI) |
