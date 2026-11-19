# Agentes, ferramentas e triagem de pedidos

Responsável: David (Engenheiro de IA). Este documento descreve o que está implementado em `agents/`, `services/triagem_service.py` e na camada de chat, como testar e o que ainda depende de outros integrantes. Reflete o código real; quando algo é decisão proposta (não confirmada pela equipe), isso está dito.

## 1. Fluxo de uma mensagem

```text
POST /api/chat
  → api/chat_controller         valida ChatRequest, traduz erros em HTTP
  → services/chat_service       sessão (em memória) + Runner do ADK
  → agents/agent.py             root_agent: decide o especialista
  → AgentTool("pedidos_agent")  o especialista recebe SÓ o texto da chamada
  → agents/tools.py             adaptadores finos
  → services/triagem_service    prazo, urgência, tipo, ausências
  → services/pedido_service     safra, capacidade, preço, produtores (Arthur)
  → repositories/*              CSV/JSON via storage
```

Princípio: **o LLM interpreta, o código verifica.** Safra, capacidade, preço, prazo e urgência são calculados por código. O agente só extrai o que o comprador escreveu e apresenta o resultado.

## 2. Componentes

| Arquivo | Papel |
|---|---|
| `agents/agent.py` | `root_agent`. Registra os especialistas como `AgentTool` (contrato da equipe). |
| `agents/subagents/pedidos_agent.py` | Agente de Pedidos (`criar_pedidos_agent`). |
| `agents/prompts.py` | Todas as instruções. O orquestrador é montado só com os especialistas registrados. |
| `agents/tools.py` | 4 ferramentas: `obter_data_atual`, `resolver_prazo_pedido`, `triar_pedido`, `consultar_pedido_recebido`. |
| `agents/modelo.py` | Escolhe o modelo: `MODEL` do `.env` ou `gemini-3.5-flash-lite`. |
| `services/triagem_service.py` | Resolução de prazo, urgência, tipo e informações ausentes. Usa o `PedidoService` sem alterá-lo. |
| `models/chat_model.py`, `services/chat_service.py`, `api/chat_controller.py` | Camada de chat (ver seção 5). |

### Contrato de plug-in dos especialistas (para Rawan e Arthur)

O `root_agent` registra automaticamente todo especialista que exponha, no módulo em `agents/subagents/`, uma fábrica:

```python
def criar_documentos_agent(model=None) -> Agent: ...   # Rawan
def criar_produtores_agent(model=None) -> Agent: ...   # Arthur + David
```

- O `name` do agente vira o nome da ferramenta (`documentos_agent`, `produtores_agent`) e aparece em `agents_used`.
- Use `description` específica: é ela que o orquestrador lê para rotear.
- Passe `model` adiante (permite injetar o LLM simulado nos testes).
- Sem a fábrica, o especialista é ignorado com um aviso no log, e o prompt do orquestrador informa que aquele domínio não está disponível (sem inventar respostas).
- As instruções não podem conter `{` ou `}` (o ADK trata `{chave}` como variável de estado); `tests/test_agents_prompts.py` cobre isso para os prompts atuais.

## 3. Ferramentas

Todas devolvem um dicionário com `status` (`"sucesso"` ou `"erro"`). Erros esperados (entrada inválida, pedido inexistente, falha de leitura de dados) viram `status: "erro"` com mensagem sem caminhos nem detalhes internos. Falhas inesperadas propagam para a retentativa do ADK 2.x.

| Ferramenta | Quando o agente a usa |
|---|---|
| `obter_data_atual` | Antes de interpretar prazo relativo; o modelo não conhece a data. |
| `resolver_prazo_pedido(expressao, data_referencia)` | Converte "pra sexta", "amanhã", "04/nov" em data. Retorna `resolvido`, `ambiguo` ou `nao_reconhecido`. |
| `triar_pedido(itens, comprador, prazo, tipo, urgencia_sinalizada, data_referencia)` | Valida o pedido em código. Nunca estima quantidade. |
| `consultar_pedido_recebido(pedido_id)` | Pedido já recebido (`PED-AAAA-NNN`). Devolve a data de recebimento como referência e omite CPFs. |

## 4. Regras determinísticas da triagem

### Prazo (`resolver_prazo`)
- Data explícita vence qualquer outra pista (`sexta (01/nov)` → 01/11).
- `hoje`, `amanhã`, `depois de amanhã` são exatos. Dia da semana → próxima ocorrência futura.
- **Ambíguo** (a ferramenta não escolhe data; o agente pergunta): `semana que vem`, `o quanto antes` e o mesmo dia da semana da referência (ex.: "quarta" numa quarta).
- Data sem ano já passada vai para o ano seguinte.
- Data ISO (`AAAA-MM-DD`) é aceita: é o formato que as ferramentas devolvem e que o modelo reaproveita ao reprocessar um pedido (achado da validação real).

### Urgência
`urgente` (entrega em até 2 dias **ou** o comprador declarou urgência), `normal` (3 a 14 dias), `planejado` (mais de 14 dias), `indefinida` (sem prazo ou prazo no passado).

### Tipo
`pedido_firme`, `cotacao`, `fornecimento_recorrente`, `nao_e_pedido`. O LLM escolhe; o código só aceita valores desse conjunto (outro valor vira erro controlado).

> **Decisão proposta, a validar com Murilo/equipe.** Os dados não trazem tipo nem urgência (`docs/DADOS.md`, seção 8). O vocabulário de tipo foi derivado das 15 mensagens de `pedidos.json` (compras, cotações PED-007/008/009/013, recorrência PED-010/011, e mensagens que não são compra PED-012/014/015) e os limiares de urgência (2 e 14 dias) são uma proposta. Estão em constantes (`TIPOS_PEDIDO`, `LIMITE_URGENTE_DIAS`, `LIMITE_PLANEJADO_DIAS`) para ajuste fácil. O `PedidoEstruturado` mantém `tipo`/`urgencia` como `str`, sem enum fechado, como combinado com Arthur.

### Informações ausentes (`informacoes_ausentes`)
Somam-se às do `PedidoService` (`comprador`, `prazo`, `quantidade:<produto>`): `unidade:<produto>`, `prazo_ambiguo`, `prazo_nao_reconhecido`, `prazo_no_passado` e `conversao_unidade:<produto>` e `capacidade_nao_comprovada:<produto>` (sem limite explícito nem lote histórico, o sistema não afirma capacidade). Quando a unidade pedida difere da tabela de preços (ex.: "caixas" × kg), não há fator de conversão nos dados: o item fica **sem valor estimado** e a unidade informada é preservada, em vez de tratar "10 caixas" como "10 kg".

Safra, capacidade, preço, produtores elegíveis, certificação e restrições continuam no `PedidoService` (Arthur).

## 5. Camada de chat

Não havia implementação de `chat_model`, `chat_service` e `chat_controller` (esqueletos) e eles são necessários para o fluxo ponta a ponta, então foram implementados de forma mínima. **Pedimos revisão do Murilo e da Raquel.**

- Requisição: `message` (1 a 4000 caracteres), `user_id` (aceita o alias `user`; padrão `anonimo`), `session_id` opcional.
- Resposta: `answer`, `session_id`, `agents_used`, `sources` (`[]` até o Agente de Documentos preencher), `status`.
- **Divergência a decidir:** o documento de contratos usa `message` na resposta e `user` na requisição como exemplo ilustrativo; o plano de tarefas, o frontend e os testes de QA usam `answer` e `user_id`. Adotamos estes últimos (o frontend lê `answer`, `reply`, `response` e `message`).
- Sessão: em memória, isolada por usuário. `session_id` desconhecido ou de outro usuário gera sessão nova, devolvida na resposta (o contexto anterior não é reaproveitado).
- Erros: 422 (corpo inválido), 503 (IA não configurada **ou chave recusada pela API**), 502 (falha do assistente). Corpo `{"detail": "..."}`, sem detalhes internos.
- Logs: sessão (prefixo), agentes acionados e tipo da exceção; nunca o conteúdo das mensagens.
- Imports do ADK são tardios: o servidor sobe (health, frontend) mesmo sem o extra `ai`.

## 6. Configuração

```powershell
pip install -e ".[dev,ai,rag]"
Copy-Item .env.example .env     # preencher GOOGLE_API_KEY
```

- `GOOGLE_API_KEY`: chave do Google AI Studio (Gemini API). Não use credenciais do Google Cloud/Vertex junto com ela.
- `MODEL=gemini-3.5-flash-lite`: identificador confirmado na documentação oficial (estável/GA) e **validado com chamadas reais** (seção 9). Free Tier: o modelo tem camada gratuita ("Free of charge"); os limites numéricos (RPM/TPM/RPD) não estão nas docs, só no painel https://aistudio.google.com/rate-limit. Na prática, cada mensagem custa de 4 a 6 chamadas ao modelo e um rajada de ~15 chamadas em cerca de 1 minuto resultou em `429 RESOURCE_EXHAUSTED`; com 30 s entre mensagens não houve 429 (uma resposta demorou ~104 s, provável backoff interno do cliente).
- Não ajustamos `temperature`, `top_p` nem `top_k`: nos Gemini 3.x o Google recomenda os valores padrão.
- `.env` está no `.gitignore`; a chave nunca é registrada em log.

## 7. Testes

```powershell
pytest                                   # suíte completa (não chama o Gemini)
pytest tests/test_triagem_service.py     # regras determinísticas
pytest tests/test_agents_tools.py        # ferramentas
pytest tests/test_agents_orquestracao.py # delegação, trajetória e sessão
pytest tests/test_chat_integracao.py     # API → agentes → serviços → repositórios
```

Os testes de agentes usam um **LLM simulado** (`tests/llm_simulado.py`): o `Runner`, o `AgentTool`, as ferramentas, os serviços e os repositórios são os reais; só o modelo é roteirizado. Isso valida a trajetória (quem foi chamado, com quais argumentos, se o resultado real da ferramenta chegou ao modelo e se não houve chamadas extras) sem custo e de forma determinística. Eles **não** validam a qualidade da extração do Gemini real.

## 8. Limitações conhecidas

- A validação real cobriu **6 turnos / 5 cenários** (seção 9), não os 15 pedidos de `pedidos.json`. Recomenda-se rodar os demais pela interface e conferir com `docs/QA_CHECKLIST.md`.
- Free Tier com limite de requisições por minuto baixo: uma demonstração com várias mensagens seguidas pode receber 429 (o `chat_service` devolve 502 nesse caso). Considere ativar o faturamento/outro tier ou espaçar as mensagens.
- Agentes de Documentos e de Produtores dependem de Rawan e Arthur; até lá o assistente informa que não responde esses assuntos.
- Sessões em memória (reiniciar o servidor apaga o contexto) e sem autenticação.
- O resumo das ferramentas internas do especialista não aparece nos eventos do orquestrador (o `AgentTool` executa um runner aninhado); por isso `agents_used` lista os especialistas, não as ferramentas.
- Capacidade é uma referência (limite explícito ou maior lote histórico), não garantia de produção futura.
- Pedidos triados não são gravados nem alocados.

## 9. Validação real com o Gemini (`gemini-3.5-flash-lite`)

Executada em 19/11/2026 pelo `ChatService` (orquestrador, `AgentTool` e ferramentas reais). Ferramentas registradas por um espião com `functools.wraps` (sem ele o ADK enxerga as ferramentas sem parâmetros e o teste é inválido).

| # | Mensagem | Resultado observado |
|---|---|---|
| 1 | "…Mercado Bom Preço precisa de 100 kg de tomate para sexta-feira." | Extraiu comprador/produto/100 kg; "sexta" → 20/11 por ferramenta; urgência `urgente`; alerta de capacidade (referência 80 kg); resposta com preço, produtor elegível e alertas; sem oferecer "anotar". |
| 2 | "30kg de queijo coalho e umas caixas de goiaba pra sexta (Restaurante Raízes)" | Queijo 30 kg com valor; goiaba **sem quantidade** e unidade "caixas" sem valor; perguntou quantas caixas e o peso de cada. |
| 2b | Follow-up: "São 10 caixas de goiaba." | Manteve o contexto (comprador e prazo); 10 caixas **sem valor** e pediu o peso por caixa. |
| 3 | "50kg de mirtilo orgânico pra semana que vem (Sorveteria Tropical)" | Prazo **ambíguo** (pediu a data); alerta `fora_de_safra`; produtora elegível. |
| 4 | PED-003 (coloquial, "uns 15kg", "urgente pra amanhã", pede PIX) | Comprador ausente → perguntou; queijo vago → pediu especificação; mel de jandaíra encontrado; recusou PIX; urgência `urgente` (20/11). |
| 5 | PED-012 (produtora pergunta saldo; cita conta bancária) | **Nenhum especialista acionado**; explicou que não consulta dados financeiros individuais; não repetiu a conta bancária. |

Achados corrigidos a partir desta validação: resposta final omitia urgência/produtores e oferecia "anotar" (prompts); data ISO não reconhecida; alerta falso de unidade para "maços"/"dúzias" (uma linha em `pedido_service.py`); "caixas" valorizada como kg.
