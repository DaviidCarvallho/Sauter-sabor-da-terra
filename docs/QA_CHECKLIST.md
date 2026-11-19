# Checklist de QA da interface — Sabor da Terra

Responsável: Raquel (Membro 5, Interface / QA).
Legenda: **OK-mock** = verificado contra o servidor simulado (`qa/mock_server.py`). **Pendente** = precisa do backend real ou de conferência manual.

> **Atualização de 19/11/2026.** O backend de chat existe e o visual mudou: fundo branco, tema sempre claro (o modo escuro foi removido) e acento verde no lugar do rosa. Os itens que citam tema escuro ou a cor goiaba descrevem o visual anterior e foram marcados abaixo. As capturas em `docs/evidencias/` mostram o visual anterior; `desktop-4-escuro.png` é histórica.

## 1. Funcional

| # | Verificação | Resultado |
|---|---|---|
| 1 | Campo de mensagem habilitado ao abrir a página | OK-mock |
| 2 | Enter envia; Shift+Enter pula linha | OK-mock (Enter) / Pendente (Shift+Enter manual) |
| 3 | Mensagem do usuário aparece na hora, alinhada à direita | OK-mock |
| 4 | Indicador de carregamento enquanto espera a resposta | OK-mock |
| 5 | Botão e campo desabilitados durante o envio (sem envio duplo) | OK-mock |
| 6 | Resposta do assistente aparece com listas, tabelas, títulos, negrito, itálico, código e links http/https | OK-mock |
| 7 | `session_id` recebido é reenviado nas mensagens seguintes, junto com um `user_id` anônimo fixo por navegador | OK-mock |
| 8 | `session_id` e a conversa sobrevivem a recarregar a página (mesma aba) | OK-mock (9 mensagens restauradas) |
| 9 | "Nova conversa" apaga o `session_id` e limpa a tela | Pendente (manual) |
| 10 | Fontes aparecem com nome do arquivo e página (quando houver) | OK-mock |
| 11 | Alertas aparecem com rótulo em texto e cor por gravidade | OK-mock |
| 12 | Sugestões de mensagem preenchem o campo e somem após o primeiro envio | OK-mock (some) / Pendente (preencher, manual) |
| 12a | "Agentes acionados" aparece sob a resposta (sem mostrar o `root_agent`) | OK-mock |

## 2. Erros e falhas

| # | Cenário | Esperado | Resultado |
|---|---|---|---|
| 13 | Servidor devolve 500 | Faixa de erro + "Tentar de novo" | OK-mock |
| 14 | Servidor devolve 503 | "Servidor indisponível" + tentar de novo | OK (testes de lógica) |
| 15 | Servidor devolve 422 | Mostra o motivo; sem tentar de novo | OK (testes de lógica) |
| 16 | Resposta 200 sem texto | "Não devolveu nenhuma resposta" | OK (testes de lógica) |
| 17 | Corpo que não é JSON | "Formato inesperado" | OK (testes de lógica) |
| 18 | Servidor desligado / sem internet | "Sem conexão" + indicador "Servidor indisponível" | Pendente (manual) |
| 19 | Resposta passa de 60 s | "Demorou demais" + tentar de novo | Pendente (manual, mensagem com "lento") |
| 20 | Rota `/api/chat` ainda não existe (404) | Mensagem explicando que a rota não está pronta | OK (testes de lógica) |
| 20a | Servidor devolve 501 (controller ainda esqueleto) | Mensagem "ainda não foi implementada", sem tentar de novo | OK-mock |
| 21 | "Tentar de novo" reenvia a última mensagem sem duplicá-la na tela | OK-mock (lógica) / Pendente (manual) |

## 3. Acessibilidade básica

| # | Verificação | Resultado |
|---|---|---|
| 22 | Toda a interface funciona só com teclado (Tab, Enter, Shift+Tab) | Pendente (manual) |
| 23 | Foco visível em botões, atalhos e campo | OK (CSS revisado) / Pendente (manual) |
| 24 | Novas mensagens são anunciadas (`role="log"`, `aria-live`) | Pendente (leitor de tela: NVDA/VoiceOver) |
| 25 | Erros anunciados (`role="alert"`) | Pendente (leitor de tela) |
| 26 | Campo tem `<label>` associado; "pular para o campo" | OK (teste estático) |
| 27 | Contraste mínimo 4,5:1 em textos | Pendente (conferir com ferramenta de contraste) |
| 28 | Alerta não depende só de cor (tem rótulo escrito) | OK |
| 29 | Animação respeita "reduzir movimento" | OK (CSS) |
| 30 | Zoom de 200% sem perder conteúdo | Pendente (manual) |

## 4. Responsividade

| # | Largura | Resultado |
|---|---|---|
| 31 | Desktop: coluna central (52rem), boas-vindas centralizadas e folhas decorativas nas laterais | OK (capturas em 1920, 1366 e 500 px em 19/11/2026) |
| 32 | 500 px (celular): cabeçalho em duas linhas, chat ocupa a tela | OK-mock (captura) |
| 33 | 360 px e 768 px | Pendente (manual) |
| 34 | Chrome / Firefox / Edge / Safari | Chrome OK-mock; demais pendentes |

## 5. Cenários de aceitação (rodar com o backend real)

O backend de chat, os três agentes e os dados já existem (`docs/ESTRUTURA.md`). O que limita a execução dos cenários é a **chave de API** (cada mensagem faz de 4 a 6 chamadas ao Gemini; Free Tier de ~15 por minuto, então espace as mensagens em ~30 s) e, para os cenários B e C, o **índice vetorial** (`python -m rag.ingestion`, já construído na máquina do David; cada máquina precisa construir o seu).

Situação da validação (19/11/2026):

| Cenário | Situação |
|---|---|
| A. Triagem de pedido | Validado pelo desenvolvedor com o Gemini real nos 15 pedidos de `pedidos.json` e em 5 cenários (ver `docs/AGENTES_E_TRIAGEM.md`, seção 9); **falta a execução de QA com captura de tela** |
| B. Consulta documental | Validado com o Gemini real em 5 perguntas, com índice construído; **falta a execução de QA com captura de tela** |
| C. Pergunta sem evidência | Validado com o Gemini real (contrato do Supermercado Extra e laudo do P005: "não encontrei"); **falta a execução de QA** |
| D. Relatório de produtor | Validado com o Gemini real (resumo, aviso, produtor inexistente e recusa em primeira pessoa); **falta a execução de QA** |

| Cenário | Mensagem de exemplo | Deve acontecer | Evidência |
|---|---|---|---|
| A. Triagem de pedido | "Preciso de 40 kg de morango e 20 kg de queijo coalho para sexta, pedido do Restaurante Brasa." | Itens, quantidades, prazo e comprador; alertas (fora de safra, acima da capacidade) quando aplicável | ☐ captura de tela |
| B. Consulta documental | "Quais produtores têm certificação orgânica vigente para mel?" | Resposta com **fontes** (arquivo e página) | ☐ captura de tela |
| C. Pergunta sem evidência | "Qual é o prazo do contrato com a distribuidora de Recife?" | Diz que **não encontrou**; não inventa dado nem fonte | ☐ captura de tela |
| D. Relatório de produtor | "Gere o resumo do mês do produtor <nome real dos dados>." | Vendas, pedidos alocados, pendências e rascunho de notificação | ☐ captura de tela |

Observação: use nomes de produtores e produtos que existam em `data/`, senão o cenário D e o A podem falhar por dado inexistente e não por defeito.

## 6. Antes de abrir o Pull Request

1. Os arquivos editam o `static/` existente no mesmo lugar, com os mesmos nomes e caminhos absolutos (`/css/style.css`, `/js/app.js`) do original. Os ids originais foram mantidos; a identidade visual agora é fundo branco com acento verde.
2. Rode `pytest` no projeto (use `$env:GOOGLE_API_KEY=""` para não gastar cota). Resultado em 19/11/2026: ver `docs/ARQUITETURA_E_DECISOES_TECNICAS.md`, seção 14.
3. Rode `uvicorn main:app --reload` e confira em http://127.0.0.1:8000 que o status mostra "Servidor online · v…".

## 7. Como rodar os testes automáticos

```
node qa/test_logica.js                        # lógica do frontend
pytest tests/test_frontend_estatico.py        # arquivos estáticos, tema e decoração
python qa/mock_server.py                      # abre http://127.0.0.1:8001 sem backend
```


## 9. Recursos do redesenho (alto padrão)

| # | Verificação | Resultado |
|---|---|---|
| 40 | Tela inicial com 4 cartões de sugestão que preenchem o campo | OK-mock |
| 41 | ~~Tema escuro automático~~ **Removido**: a página fica sempre no tema claro (fundo branco) | Substituído (`tests/test_frontend_estatico.py`) |
| 42 | Tabela de resposta com números alinhados à direita e rolagem horizontal no celular | OK-mock |
| 43 | Botão "Copiar" na resposta do assistente | Pendente (manual: permissão da área de transferência) |
| 44 | "Cancelar resposta" (botão e Esc) interrompe e devolve o texto ao campo | Pendente (manual) |
| 45 | "Ir para a última mensagem" aparece se a pessoa rolou para cima | Pendente (manual) |
| 46 | Sem rolagem horizontal da página em 390 px e 360 px | OK-mock |
| 47 | Aviso "ainda consultando" após 10 s sem resposta (palavra `lento`) | Pendente (manual) |
| 48 | Falhas 503, 501, resposta vazia e formato inesperado mostram mensagem própria | OK-mock |
| 49 | Rodar `python qa/verificar_backend.py` contra o FastAPI real | Pendente (o backend existe; exige chave de API e gasta cota) |
