# SABOR DA TERRA
## Arquitetura do Projeto e Plano de Tarefas da Equipe

**Projeto:** Assistente Inteligente para Gestão de Cooperativa Agrícola  
**Equipe:** Murilao, Rawan, David, Arthur e Raquel

---

## 1. Objetivo deste documento

Este documento explica como a estrutura do projeto Sabor da Terra deverá funcionar, desde a inicialização da aplicação até o processamento das solicitações dos usuários. Em seguida, distribui as atividades entre os cinco integrantes, respeitando os cargos e as áreas definidos pela equipe.

O projeto combina um backend em Python/FastAPI, agentes especializados com Google ADK e Gemini, uma camada RAG para consulta documental, repositórios para leitura de dados CSV/JSON e uma interface web em HTML, CSS e JavaScript.

## 1.1 Visão geral do produto

O Sabor da Terra será um assistente conversacional para apoiar a gestão de uma cooperativa agrícola. A aplicação deverá:

- Interpretar pedidos escritos em linguagem natural.
- Consultar documentos da cooperativa e apresentar as fontes utilizadas.
- Produzir informações individualizadas sobre produtores, pedidos e situação financeira.
- Identificar informações ausentes, ambiguidades e possíveis inconsistências.
- Informar quando não encontrar evidências suficientes, sem inventar respostas.

A solução será executada inicialmente em ambiente local, mantendo uma arquitetura preparada para uma futura migração de armazenamento para a nuvem.

## 1.2 Situação atual dos componentes

| Componente | Situação | Próxima necessidade |
|---|---|---|
| Fundação FastAPI | Estrutura inicial implementada, com configuração, logging, rota de saúde e frontend estático. | Ampliar as rotas e integrar os serviços. |
| Storage local | Interface e implementação local existentes. | Utilizar o storage nos repositórios e serviços. |
| Google Cloud Storage | Estrutura inicial, ainda sem implementação funcional. | Implementar somente quando a migração para nuvem for planejada. |
| Agentes ADK | Arquivos e responsabilidades definidos, mas lógica ainda precisa ser implementada. | Criar o agente principal e os especialistas. |
| RAG | Pipeline separado em arquivos, ainda precisa ser implementado. | Criar ingestão, indexação e recuperação documental. |
| Dados da cooperativa | A estrutura de diretórios está preparada. | Inserir e validar os arquivos reais CSV, JSON, PDF e DOCX. |
| Frontend | Tela inicial e verificação de saúde do backend disponíveis; chat precisa ser conectado. | Implementar envio e apresentação das mensagens. |
| Testes | Há testes iniciais e cenários previstos para os módulos. | Implementar testes funcionais para pedidos, documentos e produtores. |

---

# 2. Como a arquitetura está organizada

A aplicação foi dividida em camadas. Cada camada tem uma responsabilidade específica e conversa com as demais por contratos definidos. Essa separação evita que o agente de IA leia arquivos diretamente, que a interface implemente regras de negócio ou que os controllers acumulem lógica.

```text
Usuário
   ↓
Frontend (HTML, CSS e JavaScript)
   ↓
API (FastAPI)
   ↓
Serviços
   ↓
Agentes / Ferramentas / Repositórios / RAG
   ↓
Storage local / ChromaDB
```

## 2.1 Visão das camadas

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Interface | `static/` | Exibir o chat, receber mensagens e apresentar respostas e fontes. |
| API / HTTP | `api/` | Receber requisições, validar entradas, chamar serviços e devolver respostas JSON. |
| Modelos / contratos | `models/` | Definir formatos de entrada e saída com Pydantic. |
| Agentes | `agents/` | Interpretar intenções, decidir quais especialistas acionar e redigir respostas. |
| Serviços | `services/` | Executar regras de negócio e coordenar operações. |
| Repositórios | `repositories/` | Ler e transformar os dados da cooperativa em objetos Python. |
| RAG | `rag/` | Extrair, dividir, indexar e recuperar trechos de documentos. |
| Armazenamento | `storage/` | Fornecer acesso uniforme aos arquivos locais ou, futuramente, ao GCS. |
| Configuração e logs | `utils/` | Centralizar variáveis de ambiente e registrar eventos. |
| Qualidade | `tests/` | Verificar contratos, regras, integração e comportamento esperado. |

# 3. Inicialização: o que acontece quando o sistema liga

1. O desenvolvedor ativa o ambiente virtual e inicia o servidor com Uvicorn, executando `uvicorn main:app --reload`.
2. O Uvicorn carrega `main.py`. A aplicação FastAPI é criada, as configurações são carregadas e as rotas são registradas.
3. A rota `/api/health` fica disponível para que a interface e os testes verifiquem se o backend está ativo.
4. O FastAPI disponibiliza a pasta `static/`. Assim, o navegador recebe `index.html`, `style.css` e `app.js`.
5. As configurações são centralizadas em `utils/config.py`. Esse módulo lê as variáveis de ambiente e define, entre outras opções, o ambiente, o modelo de IA, a pasta de dados e o backend de armazenamento.
6. Quando algum módulo precisar acessar um arquivo, deverá utilizar `get_storage()`, que seleciona a implementação de armazenamento configurada.

### Comandos para execução local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn main:app --reload
```

Endereços úteis:

- Interface: `http://127.0.0.1:8000/`
- Documentação Swagger: `http://127.0.0.1:8000/docs`
- Verificação do backend: `http://127.0.0.1:8000/api/health`

---

# 4. Como uma mensagem percorre o sistema

## 4.1 Fluxo geral do chat

1. O usuário escreve uma mensagem na interface web.
2. O JavaScript envia a mensagem por HTTP para `POST /api/chat`, incluindo o texto e os identificadores de usuário/sessão necessários.
3. `api/chat_controller.py` valida o formato usando os modelos de `models/` e encaminha a solicitação para `services/chat_service.py`.
4. O `chat_service` recupera ou cria a sessão e executa o Runner do Google ADK.
5. `agents/agent.py`, o agente raiz, interpreta a intenção e decide qual agente especialista deve atuar. Uma pergunta pode exigir mais de um especialista.
6. O agente especialista utiliza funções de `agents/tools.py`. As ferramentas não devem ler arquivos diretamente; elas chamam serviços.
7. Os serviços aplicam regras de negócio e consultam repositórios ou o mecanismo RAG.
8. Os repositórios acessam os arquivos por meio da interface Storage. O RAG consulta o índice vetorial ChromaDB.
9. O resultado retorna ao agente, que redige uma resposta em português, com alertas ou fontes quando aplicável.
10. O `chat_service` devolve a resposta ao controller, que responde em JSON. O JavaScript atualiza a conversa na tela.

**Regra central:** o modelo de IA interpreta e comunica; o código convencional verifica fatos que precisam ser consistentes, como capacidade, preço, sazonalidade e valores financeiros.

## 4.2 Exemplo: triagem de um pedido

Mensagem ilustrativa:

> “Preciso de 30 kg de queijo coalho e umas caixas de goiaba para sexta-feira”.

| Etapa | Componente | O que acontece |
|---|---|---|
| 1 | Agente de Pedidos | Identifica queijo coalho, 30 kg, goiaba, quantidade de caixas não informada e prazo relativo. |
| 2 | Ferramentas | Envia os dados estruturados para as funções de validação. |
| 3 | `pedido_service` | Coordena as verificações determinísticas e aponta o que precisa ser confirmado. |
| 4 | Repositórios | Consultam catálogo, sazonalidade, preços e capacidade dos produtores. |
| 5 | Agente | Organiza os resultados, explica alertas e pergunta pela informação que falta. |

O agente não deve inventar a quantidade de caixas nem confirmar automaticamente um pedido incompleto. A expressão “sexta-feira” também precisa ser interpretada com uma data de referência confiável, fornecida pela aplicação ou por uma ferramenta.

## 4.3 Exemplo: consulta documental com RAG

1. A equipe pergunta, por exemplo, se determinado produto possui certificação orgânica válida.
2. O Agente de Documentos solicita a consulta ao `documento_service`.
3. O retriever transforma a pergunta em uma consulta vetorial e recupera os trechos mais relevantes do ChromaDB.
4. Cada trecho deve manter metadados como nome do arquivo, tipo de documento e página.
5. O serviço devolve os trechos e as fontes ao agente.
6. O agente redige uma resposta baseada nas evidências e cita o documento de origem. Se não houver evidência suficiente, informa isso claramente.

O índice não deve ser construído a cada mensagem. A ingestão será um processo separado, executado quando os documentos forem adicionados ou atualizados.

## 4.4 Exemplo: resumo de um produtor

1. O usuário solicita o resumo de um produtor ou de um período.
2. O Agente de Produtores chama ferramentas de consulta.
3. `produtor_service` reúne cadastro, pedidos e transações financeiras.
4. `relatorio_service` calcula os dados do período e organiza vendas, pedidos alocados e pendências.
5. O agente transforma os dados estruturados em um resumo compreensível e, se solicitado, redige uma notificação.

Na primeira versão, o sistema apenas prepara o texto da notificação; não envia mensagens automaticamente.

---

# 5. Explicação da estrutura de pastas e arquivos

## 5.1 Arquivos da raiz

| Arquivo | Função |
|---|---|
| `main.py` | Ponto de entrada. Cria o FastAPI, registra routers e publica o frontend estático. |
| `pyproject.toml` | Declara versão do Python, dependências principais e extras opcionais para IA, RAG, GCS e testes. |
| `.env.example` | Modelo das configurações necessárias. Deve ser copiado para `.env` no computador de cada desenvolvedor. |
| `.env` | Configuração local com possíveis credenciais. Não deve ser enviado ao Git. |
| `.gitignore` | Evita versionar segredos, ambientes virtuais, caches e índices gerados. |
| `README.md` | Apresentação, instalação, execução e orientações gerais do projeto. |

## 5.2 `api/` — entrada HTTP

É a camada que conhece FastAPI. Recebe requisições, valida dados, chama serviços e devolve respostas. Não deve implementar regras de negócio nem acessar CSV, JSON, PDFs ou ChromaDB diretamente.

| Arquivo | Responsabilidade |
|---|---|
| `health_controller.py` | Endpoint `GET /api/health`, para informar status sem expor segredos. |
| `chat_controller.py` | Futuro `POST /api/chat`: validar `ChatRequest` e chamar `chat_service`. |
| `pedidos_controller.py` | Rotas REST para listar e realizar triagem, se a interface precisar delas. |
| `documentos_controller.py` | Consulta direta e reindexação, se forem necessárias além do chat. |
| `produtores_controller.py` | Consultas e relatórios por endpoints específicos. |

## 5.3 `models/` — contratos de dados

Contém schemas Pydantic que definem o formato dos dados que entram e saem das camadas. Os modelos ajudam a validar tipos, padronizar respostas e documentar a API automaticamente. Não devem conter regras de negócio.

| Arquivo | O que representa |
|---|---|
| `health_model.py` | Resposta da verificação de saúde. |
| `chat_model.py` | Entrada e saída do chat: usuário, sessão, mensagem, resposta e agentes acionados. |
| `pedido_model.py` | Pedido bruto e estruturado: itens, unidades, prazo, comprador, urgência, tipo, alertas e dados ausentes. |
| `produtor_model.py` | Cadastro de produtores e informações relacionadas. |
| `produto_model.py` | Produtos, sazonalidade, preços e dados de lotes. |
| `documento_model.py` | Trechos recuperados, fonte, página, score e resposta documental. |
| `relatorio_model.py` | Dados do relatório individual e da notificação a ser redigida. |

## 5.4 `agents/` — interpretação e coordenação

É a camada que utiliza o Google ADK. O agente raiz coordena os especialistas. Os agentes não devem conhecer FastAPI, abrir arquivos ou implementar cálculos de negócio.

| Arquivo | Responsabilidade |
|---|---|
| `agent.py` | Define o agente raiz e registra os especialistas como agentes/ferramentas delegáveis. |
| `prompts.py` | Centraliza instruções do orquestrador e dos especialistas: idioma, limites, regras de evidência e comportamento. |
| `tools.py` | Expõe funções Python tipadas ao ADK. Cada função deve chamar um serviço. |
| `subagents/pedidos_agent.py` | Interpreta pedidos coloquiais e organiza a triagem. |
| `subagents/documentos_agent.py` | Consulta a base documental e responde com fontes. |
| `subagents/produtores_agent.py` | Redige resumos e notificações com base em dados consultados. |

A descrição das ferramentas é importante: ela ajuda o modelo a entender quando e como chamar cada função.

## 5.5 `services/` — regras de negócio

Os serviços coordenam operações. Eles não devem conhecer HTTP nem ler arquivos diretamente. São a camada ideal para testar regras sem depender de uma chamada ao modelo.

| Arquivo | Responsabilidade |
|---|---|
| `chat_service.py` | Gerencia sessões e execução do Runner do ADK; conecta API ao agente raiz. |
| `pedido_service.py` | Valida produto, safra, capacidade, urgência, tipo, ambiguidades e inconsistências. |
| `documento_service.py` | Coordena recuperação de trechos, resposta com fontes e consulta de rastreabilidade. |
| `produtor_service.py` | Reúne cadastro, pedidos e dados financeiros de um produtor. |
| `relatorio_service.py` | Calcula e organiza vendas, pedidos alocados e pendências para o agente redigir. |

## 5.6 `repositories/` — acesso aos dados

Os repositórios sabem como localizar e converter os dados da cooperativa. Eles não devem decidir regras de negócio. Por exemplo: o repositório pode retornar a disponibilidade de um produto; quem decide se um pedido é viável é o serviço.

| Arquivo | Fonte / responsabilidade |
|---|---|
| `storage_repository.py` | Leitura genérica e parsing de CSV/JSON. Evita duplicação nos demais repositórios. |
| `produtor_repository.py` | `produtores.csv`: listar, buscar e filtrar produtores. |
| `pedido_repository.py` | `pedidos.json`: consultar pedidos; na versão inicial, somente leitura. |
| `financeiro_repository.py` | `financeiro.csv`: transações por produtor/período e dados de pendências. |
| `produto_repository.py` | `sazonalidade.csv` e `tabela_precos_outubro_2026.csv`: safra e preços. |
| `lote_repository.py` | `lotes.csv`: localizar lotes e relacioná-los a produto/produtor. |
| `document_repository.py` | Listar documentos e entregar bytes de certificações, contratos e fichas técnicas. |

## 5.7 `rag/` — base de conhecimento documental

| Arquivo | Responsabilidade |
|---|---|
| `document_loader.py` | Extrair texto de PDF/DOCX e guardar metadados de origem, tipo e página. |
| `chunker.py` | Dividir o texto em trechos com tamanho e sobreposição configuráveis, preservando metadados. |
| `vector_store.py` | Módulo que conhece ChromaDB e o mecanismo de embeddings. |
| `ingestion.py` | Pipeline offline: listar documentos, extrair texto, dividir, gerar embeddings e persistir no índice. |
| `retriever.py` | Buscar trechos relevantes por similaridade e devolver texto, fonte e score. |

Fluxo de ingestão:

```text
document_repository
       ↓
document_loader
       ↓
chunker
       ↓
vector_store (ChromaDB)
```

Fluxo de pergunta:

```text
documento_service
       ↓
retriever
       ↓
vector_store
       ↓
trechos relevantes + fontes
```

O índice é um artefato derivado e poderá ser reconstruído a partir dos documentos originais.

## 5.8 `storage/` — localização física dos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `base.py` | Define o contrato Storage: `exists`, `read_bytes`, `read_text` e `list_keys`. |
| `local_storage.py` | Lê arquivos do disco local e restringe caminhos à raiz de dados. |
| `__init__.py` | `get_storage()` escolhe a implementação de acordo com `STORAGE_BACKEND`. |
| `gcs_storage.py` | Estrutura inicial para Google Cloud Storage; precisa ser implementada antes do uso. |

A vantagem é que os serviços e repositórios solicitam uma chave lógica, como `contratos/contrato.pdf`, sem precisar saber se o arquivo está no computador ou em um bucket.

## 5.9 `static/`, `utils/`, `data/`, `docs/` e `tests/`

| Pasta | Conteúdo e função |
|---|---|
| `static/` | Frontend: `index.html` estrutura a página; `css/style.css` define aparência; `js/app.js` consulta a API e futuramente enviará mensagens ao chat. |
| `utils/` | `config.py` centraliza configurações e caminhos; `logger.py` padroniza os registros de execução. |
| `data/` | Deverá conter CSV, JSON, PDFs e DOCX fornecidos para o projeto. |
| `docs/` | Documentação técnica, incluindo `ESTRUTURA.md`, com camadas, fluxos, decisões e fases. |
| `tests/` | Testes da API, armazenamento, estrutura, pedidos, documentos e produtores. |

---

# 6. Plano de trabalho por integrante

A distribuição considera os cargos e as áreas definidos pela equipe. Como Membro 1 e Membro 3 compartilham o papel de liderança técnica/arquitetura, a recomendação é dividir a liderança: Murilao coordena a arquitetura global e as integrações; David atua como co-arquiteto e assume a implementação técnica do domínio de triagem de pedidos e agentes.

## 6.1 Membro 1 — Murilao
**Cargo:** Líder Técnico / Arquiteto de Solução  
**Área:** Arquitetura

### Responsabilidades e tarefas

- [ ] Consolidar a arquitetura e manter a documentação de referência atualizada em `docs/ESTRUTURA.md`.
- [ ] Definir convenções de código, nomes, imports, tratamento de erros, logging e organização de branches/commits.
- [ ] Definir com David os contratos entre agente raiz, especialistas, ferramentas e serviços.
- [ ] Definir com Arthur os contratos entre serviços, repositórios, modelos e armazenamento.
- [ ] Definir com Rawan o contrato de entrada/saída do RAG, incluindo metadados obrigatórios de fonte e página.
- [ ] Definir com Raquel o contrato HTTP do chat: payload, resposta, sessão, erros e apresentação de fontes.
- [ ] Revisar pull requests, resolver conflitos de integração e acompanhar testes gerais.
- [ ] Planejar a ordem de integração e manter um quadro de tarefas com responsável, prioridade e estado.
- [ ] Validar a execução local e preparar a explicação arquitetural para a apresentação técnica.

**Entregas principais:** arquitetura validada; documentação atualizada; contratos entre módulos; revisão de integração; versão integrada e executável.

## 6.2 Membro 2 — Rawan
**Cargo:** Engenheira de Dados e RAG  
**Área:** Base de conhecimento

### Responsabilidades e tarefas

- [ ] Receber e conferir os documentos reais de certificações, contratos e fichas técnicas; registrar arquivos ausentes ou ilegíveis.
- [ ] Implementar `repositories/document_repository.py` para listar documentos e disponibilizar seus bytes via Storage.
- [ ] Implementar `rag/document_loader.py` para extrair texto de PDF/DOCX e preservar nome do arquivo, tipo de documento e página.
- [ ] Implementar `rag/chunker.py` com tamanho e sobreposição configuráveis; testar a divisão nos documentos reais.
- [ ] Implementar `rag/vector_store.py` para persistir e consultar embeddings no ChromaDB.
- [ ] Escolher e documentar o modelo de embeddings compatível com o ambiente Gemini/Google, após verificar disponibilidade e requisitos.
- [ ] Implementar `rag/ingestion.py` como processo separado e repetível de indexação; evitar reindexar a cada pergunta.
- [ ] Implementar `rag/retriever.py` para busca top-k, score e filtros por metadados quando úteis.
- [ ] Trabalhar com `documento_service.py` e `documentos_agent.py` para devolver evidências e fontes em formato consistente.
- [ ] Criar testes: documento encontrado, fonte/página preservadas, pergunta sem evidência e ausência de alucinação.

**Entregas principais:** documentos carregados; índice ChromaDB criado; consulta semântica funcional; trechos recuperados com fonte/página; testes do RAG.

## 6.3 Membro 3 — David
**Cargo:** Engenheiro de IA  
**Área:** Triagem de pedidos

### Responsabilidades e tarefas

- [ ] Definir, com Murilao, o comportamento do `root_agent` e a estratégia de delegação para os três especialistas.
- [ ] Implementar `agents/agent.py` com o agente principal e o registro dos especialistas conforme a versão instalada do Google ADK.
- [ ] Implementar `agents/prompts.py` com instruções claras para o orquestrador e para o Agente de Pedidos.
- [ ] Implementar `agents/tools.py` com funções tipadas que chamem serviços, sem leitura direta de arquivos.
- [ ] Implementar `agents/subagents/pedidos_agent.py` para extrair produto, quantidade, unidade, comprador e prazo de mensagens coloquiais.
- [ ] Tratar campos ausentes, expressões ambíguas, abreviações, erros de escrita e datas relativas; solicitar esclarecimentos quando necessário.
- [ ] Implementar ou alinhar `services/pedido_service.py` para validar fatos de forma determinística, sem delegar decisões de safra/capacidade ao LLM.
- [ ] Integrar o `pedido_service` aos repositórios de produtos, produtores e pedidos implementados por Arthur.
- [ ] Definir classificação de tipo e urgência com base nos dados e regras do projeto; não inventar categorias sem validar os exemplos.
- [ ] Implementar testes de triagem para pedido completo, incompleto, ambíguo, fora de safra e quantidade acima da capacidade.
- [ ] Testar o fluxo ponta a ponta: mensagem → agente → ferramenta → serviço → repositório → resposta.

**Entregas principais:** agente raiz funcional; Agente de Pedidos; ferramentas de triagem; validações determinísticas; testes e integração com dados.

## 6.4 Membro 4 — Arthur
**Cargo:** Engenheiro de Backend  
**Área:** Dados e produtores

### Responsabilidades e tarefas

- [ ] Conferir os arquivos CSV/JSON reais e documentar colunas, tipos, identificadores, unidades e formatos de data.
- [ ] Definir os schemas Pydantic em `models/pedido_model.py`, `produtor_model.py` e `produto_model.py` a partir dos arquivos reais.
- [ ] Implementar `repositories/storage_repository.py` para parsing compartilhado de CSV/JSON.
- [ ] Implementar `produtor_repository.py`, `pedido_repository.py`, `financeiro_repository.py`, `produto_repository.py` e `lote_repository.py`.
- [ ] Implementar `services/produtor_service.py` para reunir cadastro, pedidos e financeiro de um produtor.
- [ ] Implementar `services/relatorio_service.py` para calcular vendas do período, pedidos alocados e pendências.
- [ ] Implementar `services/pedido_service.py` em colaboração com David, especialmente as consultas determinísticas aos dados.
- [ ] Implementar `agents/subagents/produtores_agent.py` e as ferramentas correspondentes em conjunto com David, mantendo a redação separada dos cálculos.
- [ ] Definir como tratar dados ausentes, valores inválidos, datas e produtores sem transações.
- [ ] Criar testes para filtros, consultas, cálculos financeiros, relatórios e rastreabilidade de lotes.

**Entregas principais:** modelos coerentes com os arquivos reais; repositórios funcionais; consultas de produtores e financeiro; relatórios calculados e testados.

## 6.5 Membro 5 — Raquel
**Cargo:** Desenvolvedora de Interface / QA  
**Área:** Interface e qualidade

### Responsabilidades e tarefas

- [ ] Revisar a estrutura atual de `static/index.html`, `css/style.css` e `js/app.js`.
- [ ] Definir com Murilao e David o contrato de `POST /api/chat`: campos enviados, resposta, identificador de sessão e formato de erros.
- [ ] Habilitar o campo de mensagem e implementar envio assíncrono com `fetch` para a API.
- [ ] Exibir mensagens do usuário e do assistente, estado de carregamento e mensagens de erro.
- [ ] Preservar o `session_id` durante a conversa para que o backend possa manter o contexto.
- [ ] Exibir fontes documentais retornadas pelo backend de maneira legível (nome do arquivo e página, quando disponíveis).
- [ ] Tratar falhas de rede, resposta vazia, tempo de espera e indisponibilidade do servidor.
- [ ] Verificar acessibilidade básica, responsividade e usabilidade da interface.
- [ ] Ampliar `tests/test_api.py` e apoiar testes manuais de ponta a ponta.
- [ ] Executar cenários de aceitação: triagem de pedido, consulta documental, pergunta sem evidência e relatório de produtor.

**Entregas principais:** chat conectado ao backend; apresentação de fontes e alertas; estados de erro/carregamento; checklist de QA e evidências de teste.

---

# 7. Matriz de responsabilidades e dependências

| Atividade / componente | Responsável principal | Apoio / dependência |
|---|---|---|
| Arquitetura, padrões e integração | Murilao | David; todos os integrantes |
| Orquestrador e contratos dos agentes | David | Murilao |
| Agente de Pedidos e triagem | David | Arthur (dados/repositórios); Murilao (revisão) |
| Documentos, ingestão e RAG | Rawan | Murilao (contratos); David (agente); Arthur (Storage/repositórios) |
| Modelos e repositórios de dados | Arthur | David (campos usados na triagem); Rawan (documentos) |
| Produtores, financeiro e relatórios | Arthur | David (agente/ferramentas); Murilao (revisão) |
| Frontend e integração do chat | Raquel | David (payload/response); Murilao (contrato API) |
| Testes de regras de pedidos | David | Arthur |
| Testes de RAG e citações | Rawan | Raquel (interface); Murilao (revisão) |
| Testes de API e interface | Raquel | Murilao e responsáveis pelos módulos |
| Revisão final e apresentação técnica | Murilao | Todos |

---

# 8. Ordem recomendada de execução

As tarefas têm dependências. A equipe pode trabalhar em paralelo, mas deve combinar contratos antes de implementar módulos que dependem uns dos outros.

| Ordem | Etapa | Responsáveis | Critério para avançar |
|---|---|---|---|
| 1 | Conferir a estrutura do projeto, remover artefatos locais do compartilhamento e obter os dados reais. | Murilao + todos | Estrutura limpa e dados disponibilizados ou pendências formalizadas. |
| 2 | Definir contratos de modelos, serviços e API. | Murilao + David + Arthur + Rawan + Raquel | Campos e formatos documentados; payload do chat acordado. |
| 3 | Implementar modelos e repositórios de dados. | Arthur | CSV/JSON lidos corretamente e testes passando. |
| 4 | Implementar triagem determinística e Agente de Pedidos. | David + Arthur | Casos de pedido testados e alertas reproduzíveis. |
| 5 | Implementar ingestão, ChromaDB, recuperação e Agente de Documentos. | Rawan | Perguntas respondidas com fontes; abstenção quando não há evidência. |
| 6 | Implementar consultas de produtores, relatórios e agente. | Arthur + David | Relatórios conferidos com os dados de origem. |
| 7 | Conectar chat e apresentar resultados na interface. | Raquel + David | Fluxo completo funciona no navegador. |
| 8 | Testes integrados, correções e ensaio de demonstração. | Raquel + Murilao + todos | Cenários principais executados sem falhas críticas. |

---

# 9. Contratos que a equipe precisa combinar

Para evitar que cada integrante implemente uma parte com formatos incompatíveis, os seguintes contratos devem ser definidos e registrados antes da integração:

- **Chat:** definir nomes e tipos dos campos da requisição (`user_id`, `session_id`, `message`) e da resposta (`answer`, `session_id`, `agents_used` e `sources`/metadados quando aplicável).
- **Triagem:** definir o formato do pedido estruturado, itens, unidades, prazo, comprador, campos ausentes, ambiguidades e alertas.
- **RAG:** definir o formato de cada trecho recuperado: conteúdo, arquivo de origem, tipo, página, identificador e score.
- **Produtores/financeiro:** definir identificadores únicos, formato de datas, moeda, sinal de débito/crédito e regra para considerar uma transação pendente.
- **Erros:** padronizar respostas de validação, ausência de dados, falha de serviço, indisponibilidade de IA e sessão inválida.
- **Sessão:** decidir como gerar e devolver `session_id` e como a interface o enviará nas mensagens seguintes.
- **Agentes:** definir o nome, a descrição, as entradas e as saídas de cada ferramenta e quais serviços ela pode chamar.

---

# 10. Critérios mínimos de qualidade e aceite

| Área | Critério de aceite |
|---|---|
| Aplicação | Servidor inicia localmente, `/api/health` responde e `/docs` está disponível. |
| Pedidos | Extrai os campos presentes; não inventa quantidades; sinaliza ambiguidades e informações ausentes. |
| Validação | Sazonalidade, capacidade e regras de urgência são verificadas por código com dados de origem. |
| Documentos | Toda resposta documental apresenta fontes verificáveis; sem evidência suficiente, o sistema admite a limitação. |
| Produtores | Relatórios correspondem aos dados de cadastro, pedidos e financeiro; cálculos são testáveis. |
| Interface | Usuário envia mensagens, recebe respostas, vê carregamento/erros e mantém a sessão. |
| Segurança | Segredos não aparecem no Git nem em respostas de health/logs; caminhos de arquivos ficam restritos à raiz de dados. |
| Testes | Cada módulo entregue possui testes positivos e casos de erro; testes importantes não ficam ignorados. |

---

# 11. Pontos de atenção

- A pasta `.venv` não deve ser compartilhada nem versionada. Cada integrante deve criar seu próprio ambiente virtual a partir do `pyproject.toml`.
- O arquivo `.env` contém configurações locais e possíveis credenciais. Não deve ser enviado ao Git. O arquivo apropriado para compartilhar é `.env.example`. Se uma chave real tiver sido exposta, ela deve ser revogada e substituída.
- Os arquivos reais da cooperativa são necessários para finalizar schemas, regras e testes realistas.
- Os controllers de chat, pedidos, documentos e produtores precisam ser implementados e registrados na aplicação.
- Os agentes, prompts, ferramentas, serviços de negócio, repositórios e pipeline RAG precisam receber implementação funcional.
- O GCS ainda precisa de implementação antes de ser utilizado. A primeira versão deve continuar funcionando com armazenamento local.
- A existência de arquivos de teste não significa que os cenários foram validados. Cada funcionalidade deve ter testes executáveis.
- A sessão em memória perde o contexto ao reiniciar o servidor. A primeira versão deve documentar essa limitação.
- Não há autenticação na primeira versão, salvo se a equipe decidir incluí-la como requisito adicional.
- Pedidos processados não devem ser considerados persistidos enquanto não houver uma estratégia de gravação definida e implementada.

---

# 12. Organização de trabalho da equipe

## 12.1 Rotina sugerida

- Manter um quadro Kanban com as colunas: **A fazer**, **Em andamento**, **Em revisão**, **Bloqueado** e **Concluído**.
- Cada tarefa deve ter um responsável principal, uma descrição objetiva, arquivos envolvidos e critério de aceite.
- Fazer reuniões curtas de alinhamento para identificar bloqueios e dependências.
- Integrar por pull request; evitar que várias pessoas alterem simultaneamente os mesmos arquivos sem combinar.
- Cada integrante deve criar testes junto com a funcionalidade, e não deixar toda a validação para o final.
- Manter `README.md` e `docs/ESTRUTURA.md` atualizados quando decisões arquiteturais mudarem.

## 12.2 Definição de concluído

Uma tarefa só deve ser considerada concluída quando o código estiver implementado, integrado à branch principal de desenvolvimento, documentado quando necessário, testado e revisado por pelo menos outro integrante.

Arquivo criado com docstring, função vazia ou teste ignorado não representa funcionalidade concluída.

---

# 13. Resumo executivo

- **Murilao:** coordena a arquitetura, os padrões técnicos, os contratos entre módulos e a integração geral.
- **Rawan:** constrói a base documental, o pipeline de ingestão e o RAG.
- **David:** implementa o agente principal, a inteligência de triagem e as validações de pedidos, em parceria com Arthur.
- **Arthur:** implementa o acesso aos dados estruturados, as consultas de produtores, o financeiro e os relatórios.
- **Raquel:** conecta a interface ao backend e conduz os testes de qualidade e aceitação.

A sequência crítica é:

```text
Dados e contratos
      ↓
Modelos e repositórios
      ↓
Serviços e agentes especializados
      ↓
RAG e relatórios
      ↓
Integração do chat
      ↓
Testes integrados e demonstração
```

A equipe deve manter a distinção entre interpretação feita pelo LLM e validação feita por código, principalmente para evitar decisões incorretas sobre capacidade de produção, sazonalidade, preços e informações financeiras.

A arquitetura proposta permite que os integrantes desenvolvam partes diferentes em paralelo, desde que os contratos sejam combinados e respeitados.
