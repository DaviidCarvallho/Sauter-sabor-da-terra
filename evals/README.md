# Conjuntos de avaliação (eval sets) do ADK

Arquivos no formato `EvalSet` do Google ADK, montados a partir de execuções **reais** com o Gemini (19/11/2026):

| Arquivo | Casos |
|---|---|
| `pedidos.evalset.json` | 6 pedidos de `data/pedidos.json` (relógio fixo na data de recebimento do pedido) |
| `documentos.evalset.json` | 3 perguntas documentais (2 com evidência, 1 sem) |
| `produtores.evalset.json` | 4 casos (resumo, produtor inexistente, aviso, pergunta em primeira pessoa) |
| `test_config.json` | Critério de trajetória das ferramentas |

## O que há em cada caso

- `userContent`: a mensagem enviada.
- `intermediateData.toolUses`: os especialistas e as ferramentas chamados na execução real. Os argumentos de `*_agent` são aproximados (`request` = mensagem completa); os das ferramentas são os que o modelo realmente enviou.
- `finalResponse`: **descrição** do que a resposta deve conter, não o texto literal (o texto do LLM varia entre execuções).
- `finalSessionState.triagem_esperada` (só pedidos): tipo, urgência, tipos de alerta e informações ausentes que o **código** calculou.

## Como são usados

1. **Automático, sem custo** — `tests/test_evalsets.py`: valida o formato, confere que as ferramentas e agentes citados existem e **reexecuta `triar_pedido`** com os argumentos gravados, comparando com `triagem_esperada`. Isso protege a parte determinística (regras de safra, capacidade, prazo, urgência) contra regressões.
2. **Com o Gemini real, por demanda** — `adk eval` compara a trajetória do modelo com `toolUses`. Este comando **não foi executado** nesta entrega (consome a cota da API); o critério `ANY_ORDER` com limiar 0,8 é um ponto de partida e precisa ser ajustado após a primeira execução, pois o modelo pode variar os argumentos.
