# Agentes, ferramentas e triagem de pedidos

Responsável: David (Engenheiro de IA). Visão geral da arquitetura, diagramas e decisões: `docs/ARQUITETURA_E_DECISOES_TECNICAS.md`. Este documento detalha agentes, ferramentas e triagem. Este documento descreve o que está implementado em `agents/`, `services/triagem_service.py` e na camada de chat, como testar e o que ainda depende de outros integrantes. Reflete o código real; quando algo é decisão proposta (não confirmada pela equipe), isso está dito.

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
| `agents/subagents/documentos_agent.py` | Agente de Documentos: responde com base no RAG, citando a fonte; admite quando não encontra. |
| `agents/subagents/produtores_agent.py` | Agente de Produtores: resumos individuais e **rascunhos** de notificação (não envia). |
| `services/documento_service.py`, `models/documento_model.py` | Consulta documental: limiar de distância 0,30 (o mesmo dos testes do retriever), evidência insuficiente explícita, página nunca inventada (para `.txt` a página é omitida, pois o loader grava `page = 1`). |
| `agents/prompts.py` | Todas as instruções. O orquestrador é montado só com os especialistas registrados. |
| `agents/tools.py` | 4 ferramentas: `obter_data_atual`, `resolver_prazo_pedido`, `triar_pedido`, `consultar_pedido_recebido`. |
| `agents/modelo.py` | Escolhe o modelo: `MODEL` do `.env` ou `gemini-3.5-flash-lite`. |
| `services/triagem_service.py` | Resolução de prazo, urgência, tipo e informações ausentes. Usa o `PedidoService` sem alterá-lo. |
| `models/chat_model.py`, `services/chat_service.py`, `api/chat_controller.py` | Camada de chat (ver seção 5). |

### Contrato de plug-in dos especialistas

O `root_agent` registra automaticamente todo especialista que exponha, no módulo em `agents/subagents/`, uma fábrica:

```python
def criar_pedidos_agent(model=None) -> Agent: ...
def criar_documentos_agent(model=None) -> Agent: ...
def criar_produtores_agent(model=None) -> Agent: ...
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
| `consultar_documentos(pergunta, max_resultados)` | (Agente de Documentos) Trechos dos documentos com fonte e página; grava as fontes no estado da sessão. |
| `consultar_produtor`, `resumo_produtor`, `dados_notificacao_produtor` | (Agente de Produtores) Cadastro público, resumo financeiro calculado e dados para redigir notificação. Sem CPF, telefone, conta bancária nem texto de pedidos. |
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
Somam-se às do `PedidoService` (`comprador`, `prazo`, `quantidade:<produto>`): `unidade:<produto>`, `prazo_ambiguo`, `prazo_nao_reconhecido`, `prazo_no_passado` e `conversao_unidade:<produto>` e `capacidade_nao_comprovada:<produto>` (sem limite explícito nem lote histórico, o sistema não afirma capacidade). Quando a unidade pedida difere da tabela de preços (ex.: "caixas" × kg), não há fator de conversão nos dados: o item fica **sem valor estimado** e a unidade informada é preservada, em vez de tratar "10 caixas" como "10 kg". **Única conversão automática: dúzia ↔ unidade** (1 dúzia = 12 unidades, fator exato), registrada no alerta informativo `conversao_unidade_aplicada`. Frequência escrita na unidade ("kg/mês", "kg por semana") é descartada. Conversões de maço, caixa, saco etc. continuam pendentes de decisão da equipe.

Safra, capacidade, preço, produtores elegíveis, certificação e restrições continuam no `PedidoService` (Arthur).

## 5. Camada de chat

Não havia implementação de `chat_model`, `chat_service` e `chat_controller` (esqueletos) e eles são necessários para o fluxo ponta a ponta, então foram implementados de forma mínima. **Pedimos revisão do Murilo e da Raquel.**

- Requisição: `message` (1 a 4000 caracteres), `user_id` (aceita o alias `user`; padrão `anonimo`), `session_id` opcional.
- Resposta: `answer`, `session_id`, `agents_used`, `sources` (preenchido pelo Agente de Documentos; `[]` nas demais respostas e zerado a cada turno), `alerts` (preenchido por `triar_pedido`: `tipo`, `severidade`, `mensagem`, `produto`; alertas de safra, capacidade etc. calculados pelo código, mais as informações ausentes; zerado a cada turno) e `status`.
- **Divergência a decidir:** o documento de contratos usa `message` na resposta e `user` na requisição como exemplo ilustrativo; o plano de tarefas, o frontend e os testes de QA usam `answer` e `user_id`. Adotamos estes últimos (o frontend lê `answer`, `reply`, `response` e `message`).
- Sessão: em memória, isolada por usuário. `session_id` desconhecido ou de outro usuário gera sessão nova, devolvida na resposta (o contexto anterior não é reaproveitado).
- Erros: 422 (corpo inválido), 429 (limite de requisições da IA; tentar de novo), 503 (IA não configurada **ou chave recusada pela API**), 502 (falha do assistente). Corpo `{"detail": "..."}`, sem detalhes internos.
- Logs: sessão (prefixo), agentes acionados e tipo da exceção; nunca o conteúdo das mensagens.
- Imports do ADK são tardios: o servidor sobe (health, frontend) mesmo sem o extra `ai`.

## 6. Configuração

```powershell
pip install -e ".[dev,ai,rag]"
Copy-Item .env.example .env     # preencher GOOGLE_API_KEY
```

- `GOOGLE_API_KEY`: chave do Google AI Studio (Gemini API). Não use credenciais do Google Cloud/Vertex junto com ela.
- `MODEL=gemini-3.5-flash-lite`: identificador confirmado na documentação oficial (estável/GA) e **validado com chamadas reais** (seção 9). Free Tier: o modelo tem camada gratuita ("Free of charge"); os limites numéricos (RPM/TPM/RPD) não estão nas docs, só no painel https://aistudio.google.com/rate-limit. Na prática, cada mensagem custa de 4 a 6 chamadas ao modelo e uma rajada de ~15 chamadas em cerca de 1 minuto resultou em `429 RESOURCE_EXHAUSTED`; com 30 s entre mensagens não houve 429 (uma resposta demorou ~104 s, provável backoff interno do cliente).
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

- A validação real (seção 9) foi **manual, com uma execução por caso**: não mede qualidade de forma repetível. `evals/` guarda conjuntos de avaliação do ADK, mas `adk eval` com o Gemini real **não foi executado**.
- O Gemini às vezes responde 503 "alta demanda" (observado 1 vez em 30 execuções); o `chat_service` devolve 502 e o usuário precisa repetir a mensagem.
- Free Tier com limite de requisições por minuto baixo: uma demonstração com várias mensagens seguidas pode receber 429 (o `chat_service` devolve 429 com mensagem amigável nesse caso). Considere ativar o faturamento/outro tier ou espaçar as mensagens.
- **Agente de Documentos depende do índice vetorial**: sem `python -m rag.ingestion` executado (e `GOOGLE_API_KEY` para os embeddings), toda consulta retorna "evidência insuficiente". O limiar 0,30 foi conferido em 18 perguntas (seção 9), amostra pequena. Rastreabilidade de lotes (`lotes.csv`) não é coberta por esse agente.
- **Agente de Produtores não autentica quem pergunta**: o sistema atende a equipe; mensagens em primeira pessoa de um produtor sobre os próprios valores são recusadas pelo prompt (e o orquestrador não as encaminha), mas isso é uma salvaguarda do modelo, não controle de acesso. Autenticação continua pendente.
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

### 9.1 Os 15 pedidos de `data/pedidos.json`

Executados um a um com o relógio fixo na data de recebimento de cada pedido (o "hoje" das ferramentas), sem histórico de conversa. Uma execução por pedido; a classificação de tipo/urgência não foi comparada a um gabarito, porque os dados não trazem um.

| Aspecto | Observado |
|---|---|
| Execução | 15 de 15 concluídos. O PED-004 falhou na primeira tentativa com 503 "alta demanda" do Gemini e passou ao ser repetido |
| Especialistas | Só Pedidos: 001, 002, 003, 005, 006, 007, 008, 013. Pedidos + Documentos: 004, 009, 010, 011. Só Documentos: 014 (aviso da ADAGRO). Nenhum: 012 e 015 (produtores escrevendo sobre os próprios valores; o assistente recusou e orientou procurar a equipe) |
| Alertas estruturados | Presentes nas triagens com problema (por exemplo, 6 no PED-006 e 8 no PED-007) e ausentes no PED-005, que não tem nenhum |
| Pontos que ainda merecem atenção | PED-009: o modelo desdobrou "frutas variadas" em itens sem quantidade, o que gerou muitos alertas; PED-013: "janeiro de 2027" não é reconhecido como prazo e o sistema pergunta a data; PED-010: pedido de lista de produtos orgânicos tratado como fornecimento recorrente sem quantidade |

Achados corrigidos a partir desta rodada: nomes com descrição ("mel (aquele silvestre mesmo)", "ricota fresca") e em inglês ("Mango", "Guava", "Passion fruit") não eram encontrados no catálogo (orientação adicionada aos prompts); a unidade "kg/month" gerava pedido de conversão (a frequência agora é descartada); na primeira rodada o "hoje" informado no texto nem sempre era repassado às ferramentas, o que distorcia prazos (a validação passou a fixar o relógio via `agents.tools._hoje`).

### 9.2 Documentos e produtores

| Caso | Resultado observado |
|---|---|
| Produtores com certificação orgânica vigente para mel | José Antônio dos Santos (P002) e Débora Cristina de Melo (P018), com validade e fontes |
| Temperatura de armazenamento do queijo coalho | 2 °C a 8 °C, conferido na ficha técnica |
| Pagamento no contrato do Restaurante Raízes | PIX no ato da entrega, conferido no contrato |
| Certificação da Maria (P001) | Vigente até 15/06/2027, conferido nos dados |
| Contrato com o Supermercado Extra (não existe) | "Não encontrei essa informação nos documentos"; citou o contrato do Mercado Bom Preço como o único existente, sem atribuí-lo ao Extra |
| Laudo de queijaria do P005 (não existe) | Disse que não encontrou |
| Resumo da P001 | Totais, produtos e pedidos coerentes com `financeiro.csv` |
| Aviso para o P004 | Rascunho com pendência de R$ 1.020,00 e certificação vencendo em 01/12/2026, valores conferidos com `financeiro.csv` |
| Pendências do P003 | R$ 6.020,00 em atraso, conferido com `financeiro.csv` |
| P999 (inexistente) | "Não foi encontrado" |
| "Quanto eu vendi esse mês? Sou a produtora Maria" | Nenhum especialista; orientou procurar a equipe |

Observações: uma pergunta sobre a "política de devolução do Supermercado Extra" foi recusada pelo orquestrador sem consultar documentos (não houve invenção, mas o caminho "sem evidência" só foi exercitado quando a pergunta citava contrato ou laudo); um pedido genérico de "notificação para o P004" foi recusado até que a equipe se identificasse.

### 9.3 Índice e limiar do RAG

Índice construído em 19/11/2026 com `python -m rag.ingestion`: 20 documentos, 52 trechos, nenhuma falha. Distância do melhor trecho: 12 perguntas com resposta nos documentos ficaram entre 0,20 e 0,27; 6 perguntas sem relação com a cooperativa ficaram entre 0,36 e 0,42. O limiar 0,30 separa os dois grupos nessa amostra, que é pequena; o tamanho dos chunks (1000/150) não foi comparado com outros valores. Em duas perguntas o primeiro trecho não era do documento esperado (hortaliças × Mercado Bom Preço; inspeção da ADAGRO), embora fosse relacionado.
