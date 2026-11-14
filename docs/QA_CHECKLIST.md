# Checklist de QA da interface — Sabor da Terra

Responsável: Raquel (Membro 5, Interface / QA).
Legenda: **OK-mock** = verificado contra o servidor simulado (`qa/mock_server.py`). **Pendente** = precisa do backend real.

## 1. Funcional

| # | Verificação | Resultado |
|---|---|---|
| 1 | Campo de mensagem habilitado ao abrir a página | OK-mock |
| 2 | Enter envia; Shift+Enter pula linha | OK-mock (Enter) / Pendente (Shift+Enter manual) |
| 3 | Mensagem do usuário aparece na hora, alinhada à direita | OK-mock |
| 4 | Indicador de carregamento enquanto espera a resposta | OK-mock |
| 5 | Botão e campo desabilitados durante o envio (sem envio duplo) | OK-mock |
| 6 | Resposta do assistente aparece com listas e negrito | OK-mock |
| 7 | `session_id` recebido é reenviado nas mensagens seguintes, junto com um `user_id` anônimo fixo por navegador | OK-mock |
| 8 | `session_id` sobrevive a recarregar a página (mesma aba) | Pendente (manual) |
| 9 | "Nova conversa" apaga o `session_id` e limpa a tela | Pendente (manual) |
| 10 | Fontes aparecem com nome do arquivo e página (quando houver) | OK-mock |
| 11 | Alertas aparecem com rótulo em texto e cor por gravidade | OK-mock |
| 12 | Atalhos de exemplo preenchem o campo | Pendente (manual) |
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
| 31 | 1280 px (desktop): painel lateral + chat | OK-mock (captura) |
| 32 | 500 px (celular): atalhos viram faixa rolável, chat ocupa a tela | OK-mock (captura) |
| 33 | 360 px e 768 px | Pendente (manual) |
| 34 | Chrome / Firefox / Edge / Safari | Chrome OK-mock; demais pendentes |

## 5. Cenários de aceitação (rodar com o backend real)

Segundo `docs/ESTRUTURA.md`, hoje `api/chat_controller.py` e os agentes são esqueleto e os arquivos de `data/` ainda não foram fornecidos. Cada cenário só pode ser executado quando sua fase estiver pronta:

| Cenário | Depende de |
|---|---|
| A. Triagem de pedido | Fase 3 (dados), fase 4 (orquestrador, Agente de Pedidos e API de chat) |
| B. Consulta documental | Fase 5 (RAG e Agente de Documentos) e documentos em `data/` |
| C. Pergunta sem evidência | Fase 5 (limiar de evidência insuficiente) |
| D. Relatório de produtor | Fase 6 (Agente de Produtores) e `produtores.csv`, `financeiro.csv` |


| Cenário | Mensagem de exemplo | Deve acontecer | Evidência |
|---|---|---|---|
| A. Triagem de pedido | "Preciso de 40 kg de morango e 20 kg de queijo coalho para sexta, pedido do Restaurante Brasa." | Itens, quantidades, prazo e comprador; alertas (fora de safra, acima da capacidade) quando aplicável | ☐ captura de tela |
| B. Consulta documental | "Quais produtores têm certificação orgânica vigente para mel?" | Resposta com **fontes** (arquivo e página) | ☐ captura de tela |
| C. Pergunta sem evidência | "Qual é o prazo do contrato com a distribuidora de Recife?" | Diz que **não encontrou**; não inventa dado nem fonte | ☐ captura de tela |
| D. Relatório de produtor | "Gere o resumo do mês do produtor <nome real dos dados>." | Vendas, pedidos alocados, pendências e rascunho de notificação | ☐ captura de tela |

Observação: use nomes de produtores e produtos que existam em `data/`, senão o cenário D e o A podem falhar por dado inexistente e não por defeito.

## 6. Antes de copiar os arquivos para o repositório

1. Abra o `static/index.html` **original** e veja como ele aponta para o CSS e o JS (`css/style.css` ou `/static/css/style.css`). Faça o `index.html` novo usar o mesmo formato. Se o `main.py` monta a pasta em `/static`, os caminhos relativos do arquivo novo não carregam.
2. Rode `pytest` no projeto. O `tests/test_api.py` já testa a página inicial e os estáticos e pode esperar textos ou ids do `index.html` antigo.
3. Se a equipe já tem cores ou logotipo, troque as variáveis do início de `css/style.css` (`:root`).

## 7. Como rodar os testes automáticos

```
node qa/test_logica.js                        # lógica do frontend (13 testes)
pytest tests/test_frontend_estatico.py        # arquivos estáticos (8 testes)
python qa/mock_server.py                      # abre http://127.0.0.1:8001 sem backend
```
