# Estrutura do projeto Sabor da Terra

Este documento explica como o projeto está organizado, qual é a função de cada pasta e arquivo, e como as partes se comunicam. É o material de referência para apresentar a arquitetura.

**Legenda:** `[OK]` implementado e testado · `[ESQ]` esqueleto (cabeçalho documentado, sem lógica) · `[DADOS]` depende de arquivos ainda não fornecidos.

---

## 1. Princípios da arquitetura

1. **Separação de responsabilidades.** Cada pasta tem um papel único: receber requisições, definir contratos de dados, aplicar regras, raciocinar com IA, buscar em documentos, acessar dados, guardar arquivos.
2. **Regra de dependência: cada camada só conhece a de baixo.**

   ```text
   api  →  services  →  agents  →  tools  →  services  →  repositories / rag  →  storage
   ```

   Na prática: a camada web não sabe como o agente raciocina, o agente não sabe que existe HTTP, e **nada fora de `storage/` conhece caminhos físicos de arquivos**.
3. **O LLM interpreta; o código verifica.** O modelo entende "30kg de queijo coalho e umas caixas de goiaba pra sexta". Conferir se o produto está em safra ou se a quantidade cabe nos produtores é função de código determinístico (`services/`). Assim os alertas exigidos pelo enunciado não dependem do humor do modelo.
4. **Armazenamento atrás de uma interface.** A troca de disco local por Google Cloud Storage é feita por configuração, sem mexer em agentes ou serviços.
5. **Escopo acadêmico.** Só existe o que tem função definida. Sem abstrações que o problema não pede.

---

## 2. Árvore completa

```text
sabor-da-terra/
├── .env.example                          [OK] Modelo das variáveis de ambiente
├── .gitignore                            [OK] Protege .env, .venv e o índice vetorial
├── main.py                               [OK] App FastAPI: rotas e frontend
├── pyproject.toml                        [OK] Dependências e config do pytest
├── README.md                             [OK] Apresentação do projeto
├── agents/                               [OK] Agentes do Google ADK (isolado da web)
│   ├── agent.py                              [ESQ] root_agent: orquestrador
│   ├── prompts.py                            [ESQ] Instruções dos agentes
│   ├── tools.py                              [ESQ] Ferramentas que chamam serviços
│   └── subagents/                            [OK] Especialistas
│       ├── documentos_agent.py                   [ESQ] Agente de Documentos
│       ├── pedidos_agent.py                      [ESQ] Agente de Pedidos
│       └── produtores_agent.py                   [ESQ] Agente de Produtores
├── api/                                  [OK] Camada HTTP
│   ├── chat_controller.py                    [ESQ] POST /api/chat
│   ├── documentos_controller.py              [ESQ] Rotas de documentos (opcional)
│   ├── health_controller.py                  [OK] GET /api/health
│   ├── pedidos_controller.py                 [ESQ] Rotas de pedidos (opcional)
│   └── produtores_controller.py              [ESQ] Rotas de produtores (opcional)
├── data/                                 [OK] Dados da cooperativa
│   ├── financeiro.csv                        [DADOS] Transações set-out/2026
│   ├── lotes.csv                             [DADOS] Rastreabilidade
│   ├── pedidos.json                          [DADOS] 15 pedidos
│   ├── produtores.csv                        [DADOS] 18 produtores
│   ├── README.md                             [OK] Arquivos esperados e situação
│   ├── sazonalidade.csv                      [DADOS] Disponibilidade por mês
│   ├── tabela_precos_outubro_2026.csv        [DADOS] Preços vigentes
│   ├── certificacoes/                        [DADOS] Certificações e laudos
│   ├── contratos/                            [DADOS] Contratos
│   └── fichas_tecnicas/                      [DADOS] Fichas técnicas
├── docs/                                 [OK] Documentação
│   └── ESTRUTURA.md                          [OK] Este documento
├── models/                               [OK] Contratos de dados (Pydantic)
│   ├── chat_model.py                         [ESQ] Requisição/resposta do chat
│   ├── documento_model.py                    [ESQ] Trecho, fonte e resposta documental
│   ├── health_model.py                       [OK] Resposta do health
│   ├── pedido_model.py                       [ESQ] Pedido bruto e estruturado
│   ├── produto_model.py                      [ESQ] Produto, sazonalidade, preço, lote
│   ├── produtor_model.py                     [ESQ] Produtor e financeiro
│   └── relatorio_model.py                    [ESQ] Resumo e notificação
├── rag/                                  [OK] Consulta documental
│   ├── chunker.py                            [ESQ] Divisão em trechos
│   ├── document_loader.py                    [ESQ] PDF/DOCX → texto + metadados
│   ├── ingestion.py                          [ESQ] Pipeline de indexação
│   ├── retriever.py                          [ESQ] Busca top-k com fonte
│   └── vector_store.py                       [ESQ] ChromaDB e embeddings
├── repositories/                         [OK] Acesso a dados estruturados
│   ├── document_repository.py                [ESQ] Documentos das 3 pastas
│   ├── financeiro_repository.py              [ESQ] financeiro.csv
│   ├── lote_repository.py                    [ESQ] lotes.csv
│   ├── pedido_repository.py                  [ESQ] pedidos.json
│   ├── produto_repository.py                 [ESQ] sazonalidade e preços
│   ├── produtor_repository.py                [ESQ] produtores.csv
│   └── storage_repository.py                 [ESQ] Parsing genérico de CSV/JSON
├── services/                             [OK] Regras de negócio
│   ├── chat_service.py                       [ESQ] Runner do ADK e sessão
│   ├── documento_service.py                  [ESQ] Resposta com fontes e lotes
│   ├── pedido_service.py                     [ESQ] Validações da triagem
│   ├── produtor_service.py                   [ESQ] Cadastro, pedidos e financeiro
│   └── relatorio_service.py                  [ESQ] Dados de resumos e notificações
├── static/                               [OK] Frontend
│   ├── index.html                            [OK] Página
│   ├── css/                                  [OK]
│   │   └── style.css                             [OK] Estilos
│   └── js/                                   [OK]
│       └── app.js                                [OK] Lógica do frontend
├── storage/                              [OK] Onde os arquivos ficam
│   ├── base.py                               [OK] Interface Storage
│   ├── gcs_storage.py                        [ESQ] Google Cloud Storage
│   └── local_storage.py                      [OK] Disco local
├── tests/                                [OK] Testes
│   ├── test_api.py                           [OK] API, estáticos, docs
│   ├── test_documentos.py                    [ESQ] RAG e fontes
│   ├── test_estrutura.py                     [OK] Todos os módulos importam
│   ├── test_pedidos.py                       [ESQ] Triagem de pedidos
│   ├── test_produtores.py                    [ESQ] Relatórios e notificações
│   └── test_storage.py                       [OK] Storage local
└── utils/                                [OK] Transversal
    ├── config.py                             [OK] Configuração centralizada
    └── logger.py                             [OK] Logging
```

`__init__.py` (um por pacote Python, com a descrição da camada) e `.gitkeep` (mantêm pastas vazias no Git) foram omitidos da árvore.

### O que foi adicionado ou esclarecido em relação à estrutura original

| Item | Por quê |
|---|---|
| `models/produto_model.py`, `repositories/produto_repository.py` | `sazonalidade.csv` e `tabela_precos_outubro_2026.csv` não tinham modelo nem repositório |
| `repositories/lote_repository.py` | `lotes.csv` (rastreabilidade) não tinha repositório |
| `models/documento_model.py` | O enunciado exige citar a fonte de cada resposta documental, o que pede um modelo para fonte e trecho |
| `api/health_controller.py`, `models/health_model.py` | Endpoint `/api/health` |
| `storage/base.py` | Interface `Storage`, o contrato que local e GCS cumprem |
| `agents/subagents/__init__.py` | Torna `subagents` um pacote importável |
| `tests/test_storage.py`, `tests/test_estrutura.py` | Testam o storage e garantem que todos os módulos importam |
| `docs/`, `data/README.md` | Documentação |
| `repositories/storage_repository.py` (mantido, papel esclarecido) | Não duplica `storage/`: aqui está o **parsing** de CSV/JSON, lá estão os **backends** de armazenamento |

---

## 3. O caminho de uma mensagem

```mermaid
flowchart LR
    U["Navegador<br/>static/"] -->|POST /api/chat| C["api/<br/>chat_controller"]
    C --> S["services/<br/>chat_service"]
    S --> R["Runner do ADK<br/>+ sessão do usuário"]
    R --> O["agents/agent.py<br/>orquestrador"]
    O -->|AgentTool| P["pedidos_agent"]
    O -->|AgentTool| D["documentos_agent"]
    O -->|AgentTool| V["produtores_agent"]
    P --> T["agents/tools.py"]
    D --> T
    V --> T
    T --> SV["services/*"]
    SV --> RP["repositories/*"]
    SV --> RG["rag/*"]
    RP --> ST["storage/<br/>local ou GCS"]
    RG --> ST
    RG --> VS[("ChromaDB<br/>.vectorstore/")]
```

1. O navegador envia a mensagem para `POST /api/chat`.
2. `chat_controller` valida o corpo e entrega ao `chat_service`.
3. `chat_service` recupera a sessão do usuário (é ela que mantém o contexto da conversa) e executa o orquestrador.
4. O orquestrador decide qual especialista chamar, ou vários, e combina as respostas.
5. O especialista usa **ferramentas** (`tools.py`), que chamam **serviços**.
6. Os serviços buscam dados em **repositórios** ou trechos em **rag/**; ambos leem arquivos pela interface `Storage`.
7. A resposta volta pelo mesmo caminho, junto com a lista de agentes acionados.

---

## 4. Pasta por pasta

### Raiz do projeto

| Arquivo | Responsabilidade |
|---|---|
| `main.py` `[OK]` | Cria o app FastAPI, registra as rotas e serve o frontend. Ponto de entrada: `uvicorn main:app --reload` |
| `pyproject.toml` `[OK]` | Dependências: núcleo + extras opcionais (`ai`, `rag`, `gcs`, `dev`), instalados só quando a etapa correspondente chegar |
| `.env.example` `[OK]` | Modelo das variáveis de ambiente. O `.env` real nunca vai ao Git |
| `.gitignore` `[OK]` | Protege `.env`, `.venv`, o índice vetorial e arquivos temporários |
| `README.md` `[OK]` | Apresentação do projeto |

### `api/`: camada HTTP

**Função:** receber requisições, validar a entrada e devolver JSON. É a única camada que conhece FastAPI.
**Chama:** `services/` e `models/`. **É chamada por:** `main.py`.
**Não deve conter:** regra de negócio nem acesso a dados.

| Arquivo | Responsabilidade |
|---|---|
| `health_controller.py` `[OK]` | `GET /api/health`: verifica se a aplicação está no ar |
| `chat_controller.py` `[ESQ]` | `POST /api/chat`: porta de entrada da conversa |
| `pedidos_controller.py` `[ESQ]` | Rotas REST de pedidos. **Opcional**: só se a interface precisar |
| `documentos_controller.py` `[ESQ]` | Consulta documental direta e reindexação. **Opcional** |
| `produtores_controller.py` `[ESQ]` | Consulta de produtores e resumos. **Opcional** |

### `models/`: contratos de dados

**Função:** schemas Pydantic que descrevem o formato dos dados que circulam entre as camadas. Validam tipos e geram a documentação automática em `/docs`.
**Não deve conter:** lógica. Nem depender de `services/` ou `agents/`.

| Arquivo | Responsabilidade |
|---|---|
| `health_model.py` `[OK]` | Resposta do `/api/health` |
| `chat_model.py` `[ESQ]` | Requisição e resposta do chat (usuário, sessão, mensagem, agentes acionados) |
| `pedido_model.py` `[ESQ]` | Pedido bruto e pedido estruturado: itens, prazo, comprador, tipo, urgência, alertas |
| `produtor_model.py` `[ESQ]` | Produtor e transação financeira |
| `produto_model.py` `[ESQ]` | Produto, sazonalidade, preço e lote |
| `documento_model.py` `[ESQ]` | Trecho recuperado, fonte e resposta documental |
| `relatorio_model.py` `[ESQ]` | Resumo individual do produtor e notificação |

Os campos dos modelos de dados serão definidos **a partir das colunas reais** dos arquivos da cooperativa, e não de suposições.

### `services/`: regras de negócio

**Função:** o "o que o sistema sabe fazer". Orquestra repositórios e RAG para responder perguntas de negócio.
**Chama:** `repositories/`, `rag/`. **É chamada por:** `api/` e `agents/tools.py`.
**Não deve conter:** HTTP, nem prompts, nem acesso direto a arquivos.

| Arquivo | Responsabilidade |
|---|---|
| `chat_service.py` `[ESQ]` | Liga a API ao agente: executa o Runner do ADK mantendo a sessão |
| `pedido_service.py` `[ESQ]` | Validações da triagem: safra, capacidade, urgência, tipo, ambiguidades |
| `documento_service.py` `[ESQ]` | Resposta documental com fontes; rastreabilidade de lotes; "evidência insuficiente" |
| `produtor_service.py` `[ESQ]` | Cadastro, pedidos e financeiro de um produtor |
| `relatorio_service.py` `[ESQ]` | Dados do resumo individual e da notificação |

### `agents/`: o "cérebro" (Google ADK)

**Função:** tudo que é do ADK. É um pacote **isolado**: não conhece HTTP.
**Chama:** `services/` (via `tools.py`). **É chamado por:** `chat_service`.

| Arquivo | Responsabilidade |
|---|---|
| `agent.py` `[ESQ]` | `root_agent`: orquestrador que registra os 3 especialistas como `AgentTool` |
| `prompts.py` `[ESQ]` | Instruções dos agentes, separadas do código |
| `tools.py` `[ESQ]` | Funções Python tipadas e com docstring que o modelo pode chamar. Finas: chamam um serviço |
| `subagents/pedidos_agent.py` `[ESQ]` | Interpreta pedidos em português coloquial |
| `subagents/documentos_agent.py` `[ESQ]` | Responde com base nos documentos, citando fontes |
| `subagents/produtores_agent.py` `[ESQ]` | Gera resumos e redige notificações |

A docstring de cada ferramenta é o que o modelo lê para decidir quando usá-la. Por isso é parte do comportamento do sistema, não só documentação.

### `rag/`: consulta documental

**Função:** transformar PDFs e DOCX em um índice pesquisável e recuperar os trechos relevantes para uma pergunta.
**Chama:** `repositories/document_repository`. **É chamada por:** `services/documento_service`.

| Arquivo | Responsabilidade |
|---|---|
| `document_loader.py` `[ESQ]` | PDF/DOCX → texto + metadados (arquivo, tipo, página) |
| `chunker.py` `[ESQ]` | Divide o texto em trechos preservando a origem |
| `vector_store.py` `[ESQ]` | **Único** módulo que conhece o ChromaDB e os embeddings |
| `retriever.py` `[ESQ]` | Busca os trechos mais relevantes (top-k), com fonte e score |
| `ingestion.py` `[ESQ]` | Pipeline completo: listar → carregar → dividir → embeddings → gravar. Executável como comando e repetível |

Fluxo de **construção do índice** (offline, por comando): `ingestion` → `document_repository` → `document_loader` → `chunker` → `vector_store`.
Fluxo de **consulta** (a cada pergunta): `documento_service` → `retriever` → `vector_store`.

### `repositories/`: acesso a dados estruturados

**Função:** transformar CSV e JSON em objetos Python. Os serviços pedem "os produtores que vendem mel", não "leia a coluna 4 do CSV".
**Chama:** `storage`. **É chamada por:** `services/`.
**Não deve conter:** regra de negócio.

| Arquivo | Fonte | Responsabilidade |
|---|---|---|
| `storage_repository.py` `[ESQ]` | (genérico) | Parsing de CSV/JSON via `Storage`, compartilhado pelos demais |
| `produtor_repository.py` `[ESQ]` `[DADOS]` | `produtores.csv` | Listar e buscar produtores |
| `pedido_repository.py` `[ESQ]` `[DADOS]` | `pedidos.json` | Listar e buscar pedidos (somente leitura na v1) |
| `financeiro_repository.py` `[ESQ]` `[DADOS]` | `financeiro.csv` | Transações e pendências por produtor |
| `produto_repository.py` `[ESQ]` `[DADOS]` | `sazonalidade.csv`, `tabela_precos_outubro_2026.csv` | Safra e preços |
| `lote_repository.py` `[ESQ]` `[DADOS]` | `lotes.csv` | Rastreabilidade |
| `document_repository.py` `[ESQ]` `[DADOS]` | `certificacoes/`, `contratos/`, `fichas_tecnicas/` | Lista e entrega os bytes dos documentos |

Trocar CSV/JSON por um banco de dados no futuro significa reescrever **apenas** estes arquivos.

### `storage/`: onde os arquivos ficam

**Função:** esconder *onde* os arquivos estão. Todos acessam por **chave lógica** (`contratos/mercado_bom_preco.pdf`), nunca por caminho.
**Escolha do backend:** variável `STORAGE_BACKEND` (`local` ou `gcs`).

| Arquivo | Responsabilidade |
|---|---|
| `base.py` `[OK]` | Interface `Storage`: `exists`, `read_bytes`, `read_text`, `list_keys` |
| `local_storage.py` `[OK]` | Implementação em disco; bloqueia chaves que saem da pasta de dados (`../`) |
| `__init__.py` `[OK]` | Fábrica `get_storage()`, que escolhe o backend pela configuração |
| `gcs_storage.py` `[ESQ]` | Implementação para Google Cloud Storage. Contrato definido, corpo pendente |

### `data/`: dados da cooperativa

Arquivos CSV/JSON e documentos fictícios fornecidos no enunciado. Veja `data/README.md` para a lista e a situação de cada um. Nada aqui é inventado: se o arquivo não chegou, ele não existe.

### `static/`: frontend

HTML5, CSS3 e JavaScript puro. Hoje mostra a identidade visual e o status do servidor. A interface de chat será conectada a `POST /api/chat`.

| Arquivo | Responsabilidade |
|---|---|
| `index.html` `[OK]` | Estrutura da página |
| `css/style.css` `[OK]` | Estilos |
| `js/app.js` `[OK]` | Consulta `/api/health`; receberá a lógica do chat |

### `utils/`: transversal

| Arquivo | Responsabilidade |
|---|---|
| `config.py` `[OK]` | **Única** leitura das variáveis de ambiente, tipada. Resolve caminhos absolutos. Chaves ficam mascaradas |
| `logger.py` `[OK]` | Logging padronizado (`get_logger(__name__)`) |

### `tests/`

| Arquivo | O que verifica |
|---|---|
| `test_api.py` `[OK]` | `/api/health`, página inicial, estáticos, documentação automática |
| `test_storage.py` `[OK]` | Leitura, listagem, erros e bloqueio de `../` |
| `test_estrutura.py` `[OK]` | Todos os módulos da estrutura existem e importam |
| `test_pedidos.py`, `test_documentos.py`, `test_produtores.py` `[ESQ]` | Casos previstos documentados; ficam *skipped* até a fase correspondente |

---

## 5. Como agentes, serviços e repositórios conversam

Exemplo com o pedido do enunciado: *"preciso de 30kg de queijo coalho e umas caixas de goiaba pra sexta"*.

1. O **orquestrador** reconhece um pedido e chama o **Agente de Pedidos**.
2. O agente (LLM) extrai o que o texto diz: queijo coalho, 30 kg; goiaba, em caixas, quantidade não informada; prazo "sexta".
3. Ele chama uma **ferramenta** de validação (`tools.py`) com esses dados já estruturados.
4. A ferramenta chama o `pedido_service`, que consulta `produto_repository` (safra) e `produtor_repository` (capacidade). Tudo em código, sem LLM.
5. O serviço devolve um resultado verificável: alertas (ex.: produto fora de safra), informações ausentes (quantidade de caixas), urgência.
6. O agente redige a resposta para a equipe, apontando o que falta.

**Ponto de atenção:** "sexta" só vira uma data se o agente souber a data de hoje. A data atual precisa ser fornecida ao agente (prompt ou ferramenta); o modelo não a conhece.

---

## 6. Como o sistema acessa arquivos locais

```text
DATA_DIR (.env)  →  Settings.data_path (caminho absoluto)  →  LocalStorage(root)
                                                                     ▲
repositories / rag  ──  get_storage().read_text("pasta/arquivo.csv")─┘
```

- `DATA_DIR` é resolvido para caminho absoluto, então o servidor funciona de qualquer pasta.
- Quem precisa de um arquivo pede por **chave lógica** relativa à raiz dos dados, sempre com `/`.
- `LocalStorage` recusa chaves que escapam da raiz (ex.: `../.env`), o que é testado.

---

## 7. Migração futura para a nuvem

Mover o sistema para a nuvem envolve **quatro peças diferentes**, e o GCS resolve só a primeira.

| Peça | Hoje (local) | Na nuvem | Esforço |
|---|---|---|---|
| Arquivos (CSV, JSON, PDF, DOCX) | `LocalStorage` | `GCSStorage` com `STORAGE_BACKEND=gcs` | Baixo: implementar um arquivo |
| Índice vetorial | ChromaDB em `.vectorstore/` | Reconstruir pela ingestão a partir do GCS, ou persistir o ChromaDB em disco/volume do serviço | Médio. **O GCS não substitui o banco vetorial** |
| Sessões (contexto) | Em memória | Sessão persistente (o ADK oferece serviço de sessão em banco; no diagrama de referência é o Firestore) | Médio |
| Logs | `logger.py` | Cloud Logging | Baixo |

A escolha entre as opções do índice vetorial será feita na fase do RAG.

---

## 8. Requisitos do enunciado → componentes

| Requisito (PDF) | Componente |
|---|---|
| Interface conversacional por texto | `static/` + `POST /api/chat` |
| Processar pedidos em português coloquial, com abreviações e erros | `agents/subagents/pedidos_agent.py` |
| Extrair produtos, quantidades, prazos e comprador; classificar por tipo e urgência | Agente de Pedidos + `pedido_service` |
| Sinalizar produto fora de safra e quantidade acima da capacidade | `pedido_service` (código determinístico) |
| Responder sobre o acervo indicando o documento de origem | `rag/` + `documento_service` + `models/documento_model.py` |
| Dizer claramente quando não souber, sem inventar | Limiar de evidência no `documento_service` + regras em `prompts.py` |
| Rastreabilidade de lote | `lote_repository` + `documento_service` |
| Gerar relatórios e notificações de forma autônoma | `relatorio_service` + Agente de Produtores |
| Manter o contexto ao longo da sessão | Sessão por usuário em `chat_service` |

---

## 9. Decisões e alternativas

| Decisão | Alternativa considerada | Por que esta |
|---|---|---|
| Orquestrador com `AgentTool` | `sub_agents` (transferência de controle) | Perguntas reais cruzam especialistas (ex.: disponibilidade e certificação de um produto) e o orquestrador precisa combinar as respostas. Limitação: o especialista recebe só o texto da chamada, não o histórico inteiro |
| Camadas `agents → tools → services → repositories → storage` | Tools lendo os arquivos direto | Troca de armazenamento e de fonte de dados sem tocar nos agentes; serviços testáveis sem LLM |
| LLM interpreta, código valida | Deixar o LLM decidir safra e capacidade | Confiabilidade: os alertas exigidos pelo enunciado não podem variar de uma execução para outra |
| CSV/JSON via repositórios | Banco de dados (SQLite) | Escopo acadêmico e dados pequenos. Os repositórios permitem trocar depois |
| ChromaDB local | Serviço vetorial gerenciado | Simples para rodar localmente. Migração planejada como peça própria |
| Controllers REST de pedidos/documentos/produtores opcionais | Criá-los todos agora | O fluxo principal passa pelo chat; só se cria o que a interface usar |
| Frontend em JavaScript puro | Framework (React) | Exigência do escopo inicial e menos dependências |

---

## 10. Limitações conhecidas

- **Sessão em memória:** reiniciar o servidor apaga o contexto das conversas.
- **Sem autenticação:** adequado ao protótipo, não à produção.
- **Pedidos somente leitura:** o resultado da triagem aparece no chat, mas não é gravado.
- **Qualidade do RAG depende do chunking e dos embeddings**, que serão calibrados com os documentos reais.
- **Erros semânticos de extração:** os serviços detectam inconsistências de fato (safra, capacidade), mas não conseguem saber se o LLM entendeu o pedido errado.
- **Notificações só são redigidas**, não enviadas.
- **Nada de dados da cooperativa foi usado até agora:** os arquivos ainda não foram fornecidos.

## 11. Decisões em aberto

| Decisão | Depende de |
|---|---|
| Modelo Gemini (`MODEL`) | Escolha na lista vigente do AI Studio |
| Modelo de embeddings | Qualidade com os documentos reais e custo |
| Tamanho e sobreposição dos chunks | Teste com os documentos reais |
| Valores de "tipo" e "urgência" de pedido | Análise de `pedidos.json` |
| Limiar para "evidência insuficiente" | Teste com perguntas reais |
| Persistir pedidos processados | Decisão do projeto |
| Quais controllers REST opcionais ativar | Necessidade da interface |

---

## 12. Fases de desenvolvimento

| Fase | Entrega | Situação |
|---|---|---|
| 1 | Fundação: FastAPI, configuração, `/api/health`, storage local, frontend mínimo | Concluída |
| 2 | Estrutura completa e documentação | Esta entrega |
| 3 | Dados e repositórios (CSV/JSON) e modelos | Pendente (depende dos arquivos de `data/`) |
| 4 | Orquestrador, Agente de Pedidos e API de chat | Pendente |
| 5 | RAG e Agente de Documentos | Pendente |
| 6 | Agente de Produtores, relatórios e notificações | Pendente |
| 7 | Interface de chat conectada à API | Pendente |
| Futuro | GCS, Docker, proteções de entrada e saída | Fora do escopo atual |
