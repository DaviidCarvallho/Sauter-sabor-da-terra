# Contratos de Integração

Este documento estabelece os contratos de comunicação e integração entre os componentes do projeto **Sauter – Sabor da Terra**, com o objetivo de padronizar as responsabilidades, entradas, saídas e dependências entre os módulos desenvolvidos pela equipe.

Os contratos devem ser utilizados como referência durante a implementação e integração dos componentes, evitando dependências indevidas entre camadas, duplicação de responsabilidades e inconsistências na comunicação entre os módulos.

Os detalhes específicos de implementação devem respeitar a arquitetura definida em `docs/ESTRUTURA.md`.

---

## 1. Visão geral da arquitetura

A aplicação é organizada em camadas com responsabilidades bem definidas:

- **API:** recebe e valida as requisições HTTP e encaminha as operações para os serviços.
- **Services:** concentram as regras de negócio determinísticas e coordenam o acesso aos dados.
- **Agents:** interpretam as solicitações em linguagem natural, decidem quais especialistas devem ser acionados e elaboram as respostas.
- **Tools:** disponibilizam funções para os agentes, atuando como adaptadores entre os agentes e os serviços.
- **Repositories:** acessam e transformam os dados estruturados, como CSV e JSON.
- **RAG:** realiza a ingestão, indexação e recuperação de informações presentes em documentos.
- **Storage:** abstrai o acesso físico aos arquivos, permitindo diferentes implementações de armazenamento.

O fluxo geral de dependências e comunicação é:

`API → chat_service → agents → tools → services → repositories / RAG → storage`

Essa representação descreve o fluxo principal de comunicação, não uma dependência obrigatória entre todos os componentes. Por exemplo, o `chat_service` possui responsabilidade específica de integração com o ADK, enquanto os demais serviços de domínio não devem depender dos agentes.

### 1.1. Princípios de integração

1. Cada componente deve conhecer somente as responsabilidades necessárias para executar sua função.
2. A camada de API não deve implementar regras de negócio.
3. Os agentes não devem conhecer detalhes de HTTP, repositórios ou armazenamento físico.
4. As tools devem atuar como interfaces entre agentes e serviços, sem reproduzir regras de negócio.
5. As regras de negócio determinísticas devem ser implementadas nos serviços, e não delegadas exclusivamente ao modelo de linguagem.
6. Os repositórios devem cuidar do acesso e da transformação dos dados, sem implementar regras de negócio.
7. Somente a camada `storage/` deve conhecer os detalhes físicos de acesso aos arquivos.
8. O acesso aos arquivos deve utilizar chaves lógicas, sem expor caminhos físicos às demais camadas.
9. Os modelos Pydantic devem representar e validar os dados que transitam entre as camadas, sem concentrar regras de negócio.
10. A comunicação entre os componentes deve respeitar os contratos definidos neste documento.

---

## 2. Contrato entre o agente orquestrador e os agentes especialistas

O agente principal, localizado em `agents/agent.py`, é responsável por interpretar a solicitação do usuário, identificar os domínios envolvidos e acionar os agentes especialistas necessários.

Os agentes especialistas são:

- `documentos_agent.py`: responsável por solicitações relacionadas a documentos e informações presentes nos materiais da cooperativa.
- `pedidos_agent.py`: responsável por solicitações relacionadas a pedidos, produtos, disponibilidade e informações comerciais.
- `produtores_agent.py`: responsável por solicitações relacionadas aos produtores e suas informações.

A comunicação entre o agente principal e os especialistas deve ocorrer por meio de `AgentTool`, conforme definido na arquitetura.

### 2.1. Entrada dos agentes especialistas

O agente especialista deve receber exclusivamente o texto da chamada realizada pelo agente orquestrador.

Exemplo:

```text
Consulte a disponibilidade de 30 kg de queijo coalho para sexta-feira e informe possíveis produtores.
```

**Não deve ser encaminhado automaticamente o histórico completo da conversa ao agente especialista.**

Essa decisão é intencional e tem como finalidade limitar o compartilhamento de informações entre os agentes, contribuindo para a proteção dos dados e para a redução da exposição de informações que não sejam necessárias à execução da tarefa.

Caso alguma informação de uma interação anterior seja indispensável para a solicitação atual, o próprio agente orquestrador deverá incorporá-la explicitamente ao texto da chamada, compartilhando apenas o contexto estritamente necessário.

### 2.2. Responsabilidades do agente orquestrador

- Interpretar a solicitação original do usuário.
- Identificar quais domínios estão relacionados à solicitação.
- Selecionar e acionar um ou mais agentes especialistas.
- Formular chamadas com informações suficientes para a execução da tarefa.
- Evitar encaminhar informações desnecessárias aos especialistas.
- Combinar e organizar as respostas recebidas.
- Produzir uma resposta final coerente para o usuário.

### 2.3. Responsabilidades dos agentes especialistas

- Atuar exclusivamente no domínio de sua responsabilidade.
- Interpretar o texto recebido do agente orquestrador.
- Acionar as tools disponíveis quando necessário.
- Utilizar os resultados fornecidos pelos serviços para elaborar suas respostas.
- Informar quando não houver dados suficientes para responder.
- Não inventar informações que não estejam presentes nos dados ou documentos consultados.

### 2.4. Saída dos agentes especialistas

O agente especialista deve retornar uma resposta textual ao agente orquestrador, contendo as informações relevantes obtidas durante a execução.

A resposta deve:

- Ser objetiva e relacionada à solicitação recebida.
- Apresentar resultados e alertas retornados pelos serviços.
- Indicar informações ausentes ou insuficientes quando necessário.
- Não apresentar como confirmado aquilo que não foi validado pelos dados.

Não é necessário estabelecer um formato genérico de retorno independente do mecanismo de execução do ADK. A integração deve respeitar o formato de resposta utilizado pelo framework, cabendo ao agente orquestrador interpretar e combinar os resultados.

---

## 3. Contrato entre agentes, tools e serviços

As tools, localizadas em `agents/tools.py`, representam as funções que os agentes podem executar para consultar ou manipular informações da aplicação.

Elas devem funcionar como adaptadores entre a interpretação realizada pelos agentes e as operações determinísticas disponibilizadas pelos serviços.

### 3.1. Responsabilidades das tools

- Disponibilizar funções com nomes e descrições claros para os agentes.
- Declarar parâmetros e tipos de dados de maneira explícita.
- Validar os parâmetros de entrada quando necessário.
- Encaminhar a solicitação ao serviço responsável.
- Retornar os resultados fornecidos pelo serviço em formato compreensível para o agente.
- Comunicar erros de execução de maneira adequada.

As tools não devem:

- Implementar regras de negócio.
- Acessar arquivos diretamente.
- Consultar repositórios diretamente.
- Implementar operações de leitura de CSV ou JSON.
- Duplicar funcionalidades já existentes nos serviços.

### 3.2. Responsabilidades dos serviços

Os serviços, localizados em `services/`, concentram as regras de negócio determinísticas da aplicação.

Eles devem:

- Receber os parâmetros encaminhados pelas tools ou pela API.
- Executar validações e regras de negócio.
- Coordenar consultas aos repositórios e ao RAG.
- Consolidar os resultados obtidos.
- Retornar informações estruturadas para o componente solicitante.
- Informar situações em que os dados disponíveis não sejam suficientes para concluir uma operação.

Os serviços de domínio não devem depender dos agentes, conhecer prompts ou implementar comunicação HTTP.

**Exceção arquitetural:** o `chat_service.py` possui responsabilidade específica de integração entre a API e o agente principal. Ele deve gerenciar a sessão da conversa e executar o agente por meio do ADK Runner. Essa exceção não deve ser reproduzida nos demais serviços.

### 3.3. Exemplo de fluxo

Para uma solicitação como:

```text
Preciso de 30 kg de queijo coalho e algumas caixas de goiaba para sexta-feira.
```

O fluxo esperado é:

1. O agente orquestrador identifica que a solicitação está relacionada a pedidos.
2. O agente orquestrador aciona o especialista de pedidos, encaminhando somente o texto necessário para a execução.
3. O especialista interpreta os produtos, quantidades e prazo.
4. O especialista aciona a tool responsável pela consulta de disponibilidade.
5. A tool encaminha os parâmetros ao `pedido_service`.
6. O serviço consulta os repositórios necessários, como `produto_repository` e `produtor_repository`.
7. O serviço aplica as regras determinísticas, verifica os dados disponíveis e identifica alertas ou informações ausentes.
8. A tool retorna o resultado ao agente especialista.
9. O especialista elabora uma resposta com base nos resultados.
10. O agente orquestrador recebe a resposta e a incorpora à resposta final.

A interpretação de expressões como "sexta-feira" pode ser realizada pelo modelo, mas a resolução da data deve utilizar uma referência temporal confiável, como a data atual fornecida pelo contexto ou por uma ferramenta apropriada. Não se deve depender de uma suposição temporal do modelo.

---

## 4. Contrato entre serviços, repositórios, modelos e armazenamento

A comunicação entre serviços, repositórios, modelos e armazenamento deve respeitar a separação de responsabilidades estabelecida na arquitetura.

### 4.1. Models

Os modelos, localizados em `models/`, representam os dados utilizados na comunicação entre as camadas.

Responsabilidades:

- Definir a estrutura dos dados.
- Declarar os tipos dos atributos.
- Validar os dados recebidos.
- Padronizar os formatos de entrada e saída.

Os modelos devem utilizar Pydantic e não devem conter regras de negócio ou depender de serviços, agentes e repositórios.

Exemplos:

- `chat_model.py`: estruturas de entrada e saída das operações de chat.
- `documento_model.py`: estruturas relacionadas a documentos.
- `pedido_model.py`: estruturas relacionadas a pedidos.
- `produto_model.py`: estruturas relacionadas a produtos.
- `produtor_model.py`: estruturas relacionadas a produtores.
- `relatorio_model.py`: estruturas relacionadas a relatórios.

### 4.2. Repositories

Os repositórios, localizados em `repositories/`, são responsáveis pelo acesso e pela transformação dos dados estruturados.

Responsabilidades:

- Ler dados disponibilizados pela camada de armazenamento.
- Interpretar arquivos CSV e JSON.
- Converter os registros em objetos Python ou estruturas compatíveis com os modelos.
- Disponibilizar operações de consulta para os serviços.
- Centralizar a lógica de acesso aos dados estruturados.

Os repositórios não devem implementar regras de negócio, acessar diretamente caminhos físicos ou depender dos agentes.

O `storage_repository.py` possui uma função específica de leitura e interpretação de dados estruturados, como CSV e JSON. Ele não deve ser confundido com a abstração de armazenamento localizada em `storage/`.

### 4.3. Services

Os serviços são responsáveis pela lógica de negócio e pela coordenação das operações da aplicação.

Responsabilidades:

- Receber dados de entrada.
- Aplicar regras e validações de negócio.
- Consultar um ou mais repositórios.
- Acionar operações de recuperação documental quando necessário.
- Consolidar informações.
- Retornar resultados estruturados.

Os serviços não devem acessar arquivos diretamente, implementar lógica de transporte HTTP ou depender dos agentes de inteligência artificial.

### 4.4. Storage

A camada `storage/` abstrai o acesso físico aos arquivos.

Ela deve disponibilizar uma interface comum para operações como:

- Verificar a existência de um arquivo.
- Ler arquivos em bytes.
- Ler arquivos em texto.
- Listar chaves disponíveis.

As implementações, como `local_storage.py` e `gcs_storage.py`, devem respeitar a abstração definida em `base.py`.

Os demais componentes devem utilizar chaves lógicas para localizar os arquivos, sem conhecer diretórios ou caminhos físicos.

Essa separação permite alterar a implementação de armazenamento sem exigir modificações nos serviços e repositórios que consomem os dados.

---

## 5. Contrato do RAG

O módulo RAG, localizado em `rag/`, é responsável pela ingestão, indexação e recuperação de informações presentes nos documentos da cooperativa.

A integração deve considerar dois fluxos distintos: ingestão documental e recuperação de informações.

### 5.1. Fluxo de ingestão documental

A ingestão ocorre quando documentos são processados para disponibilizar seu conteúdo para consultas futuras.

Fluxo esperado:

```text
ingestion
    → document_repository
        → document_loader
            → chunker
                → vector_store
```

Responsabilidades:

- `ingestion.py`: coordena o processo de ingestão.
- `document_repository.py`: localiza os documentos e disponibiliza seus conteúdos.
- `document_loader.py`: realiza o carregamento e a extração do conteúdo dos documentos.
- `chunker.py`: divide o conteúdo em partes menores para indexação.
- `vector_store.py`: armazena os vetores e metadados utilizados na recuperação.

O processamento deve preservar os metadados necessários para identificar a origem dos trechos indexados.

### 5.2. Fluxo de recuperação

A recuperação ocorre durante uma solicitação que exige informações presentes nos documentos.

Fluxo esperado:

```text
documento_service
    → retriever
        → vector_store
```

Responsabilidades:

- `documento_service.py`: recebe a solicitação e coordena a operação de consulta documental.
- `retriever.py`: realiza a recuperação dos trechos relevantes.
- `vector_store.py`: consulta a base vetorial e retorna os trechos e seus metadados.

O serviço deve receber os resultados da recuperação e disponibilizar as informações ao componente solicitante.

### 5.3. Contrato de entrada

A consulta deve receber, no mínimo, uma pergunta ou texto de busca.

Exemplo:

```text
Quais são as condições de armazenamento do queijo coalho?
```

Parâmetros adicionais, como quantidade de resultados ou filtros de documentos, podem ser utilizados conforme a implementação do RAG.

### 5.4. Contrato de saída

A recuperação deve disponibilizar os trechos relevantes e seus metadados de origem.

Cada trecho recuperado deve preservar, sempre que disponível:

- `content`: conteúdo textual do trecho.
- `source`: identificação do documento de origem.
- `page`: número da página de origem, quando aplicável e disponível.

O campo `source` deve ser preservado para permitir a identificação do documento consultado. O campo `page` deve ser informado quando a estrutura do documento permitir identificar a página; caso contrário, deve ser representado como indisponível, sem inventar um número.

Esses metadados são importantes para permitir rastreabilidade e apresentação das fontes ao usuário.

### 5.5. Responsabilidades e restrições

- O RAG deve ser utilizado para informações provenientes de documentos.
- O acesso aos documentos deve respeitar a integração com `document_repository` e a abstração de armazenamento.
- O `vector_store.py` deve ser o único módulo responsável por conhecer os detalhes específicos do ChromaDB e dos embeddings.
- Os serviços devem consumir o RAG por meio das interfaces disponibilizadas, sem acessar diretamente a implementação do banco vetorial.
- A recuperação deve retornar os metadados de origem junto aos trechos.
- O agente não deve apresentar informações documentais como fatos confirmados quando não houver evidência recuperada suficiente.

---

## 6. Contrato entre API, chat_service e frontend

A comunicação entre o frontend e o backend ocorre por meio da API HTTP, utilizando o endpoint de chat.

### 6.1. Endpoint

```http
POST /api/chat
```

A API é responsável por receber a solicitação, validar os dados de entrada e encaminhar a operação ao `chat_service`.

O controlador não deve executar diretamente o agente, acessar repositórios ou implementar regras de negócio.

### 6.2. Requisição

A requisição deve conter os dados necessários para identificar a conversa e a mensagem enviada pelo usuário.

Exemplo ilustrativo:

```json
{
  "user": "Usuário",
  "session_id": "identificador-da-sessao",
  "message": "Quais produtos estão disponíveis nesta semana?"
}
```

Responsabilidades dos campos:

- `user`: identificação ou informação do usuário conforme a estrutura definida no modelo de chat.
- `session_id`: identificador da sessão da conversa, quando existente.
- `message`: texto enviado pelo usuário.

A estrutura definitiva dos campos e seus tipos deve ser mantida em conformidade com `models/chat_model.py`.

### 6.3. Processamento da requisição

O fluxo esperado é:

1. O frontend envia a mensagem para `/api/chat`.
2. O `chat_controller.py` valida a requisição.
3. O controlador encaminha os dados ao `chat_service.py`.
4. O serviço recupera ou inicializa a sessão da conversa.
5. O serviço executa o agente principal por meio do ADK Runner.
6. O agente orquestrador decide quais especialistas devem ser acionados.
7. Os especialistas utilizam tools e serviços para consultar as informações necessárias.
8. O agente principal consolida as respostas.
9. O `chat_service` organiza o resultado e o retorna à API.
10. A API disponibiliza a resposta ao frontend.

A gestão da sessão e a integração com o ADK devem permanecer no `chat_service`, e não no controlador ou nos agentes especialistas.

### 6.4. Resposta

A resposta deve disponibilizar a mensagem elaborada pelo agente principal e os dados necessários para a continuidade da conversa.

Exemplo ilustrativo:

```json
{
  "session_id": "identificador-da-sessao",
  "message": "Temos os seguintes produtos disponíveis...",
  "agents_used": [
    "pedidos_agent"
  ],
  "sources": [],
  "status": "success"
}
```

Responsabilidades dos campos:

- `session_id`: identificador da sessão utilizada.
- `message`: resposta final apresentada ao usuário.
- `agents_used`: identificação dos agentes especialistas acionados durante a execução.
- `sources`: fontes documentais utilizadas, quando houver recuperação de informações pelo RAG.
- `status`: indicação do resultado da operação.

O campo `sources` não deve ser obrigatório para todas as respostas. Solicitações respondidas exclusivamente com dados estruturados, por exemplo, podem não possuir fontes documentais.

Quando houver fontes, devem ser preservadas as informações de identificação do documento e da página, quando disponível.

A nomenclatura e os tipos definitivos devem permanecer alinhados ao `chat_model.py`.

---

## 7. Tratamento de erros e exceções

Os componentes devem tratar erros de acordo com suas responsabilidades, evitando que falhas internas sejam apresentadas diretamente ao usuário.

### 7.1. API

A API deve:

- Validar os dados recebidos.
- Identificar erros de requisição.
- Encaminhar exceções dos serviços para respostas HTTP apropriadas.
- Não expor detalhes internos, caminhos físicos, credenciais ou informações sensíveis.

### 7.2. Services

Os serviços devem:

- Identificar falhas nas operações de negócio.
- Tratar situações de dados inexistentes ou insuficientes.
- Propagar exceções de maneira consistente quando não puderem resolver a falha.
- Evitar ocultar erros que comprometam a confiabilidade da resposta.

### 7.3. Repositories e Storage

Os repositórios e a camada de armazenamento devem:

- Tratar falhas de leitura e acesso aos arquivos.
- Identificar arquivos inexistentes ou inválidos.
- Informar falhas de interpretação dos dados.
- Propagar erros para a camada responsável por decidir como a operação deve prosseguir.

### 7.4. Agents e Tools

As tools devem comunicar falhas de execução de forma compreensível para o agente.

Os agentes não devem transformar uma falha de consulta em uma informação fictícia. Quando não houver dados suficientes ou ocorrer uma falha que impeça a consulta, a resposta deve indicar a limitação.

### 7.5. Padronização

A API deve converter exceções conhecidas em respostas HTTP adequadas, evitando retornar detalhes técnicos internos ao frontend.

Os formatos específicos de erro devem ser mantidos consistentes com os modelos e padrões adotados no backend.

---

## 8. Logging

O registro de eventos deve utilizar a estrutura centralizada disponibilizada em `utils/logger.py`.

Os componentes devem registrar informações relevantes para depuração e acompanhamento da execução, respeitando os limites de privacidade.

Devem ser registrados, quando pertinentes:

- Início e conclusão de operações.
- Erros e exceções.
- Falhas de leitura ou acesso aos dados.
- Execução de consultas documentais.
- Identificação dos agentes acionados.
- Falhas de integração entre componentes.

Não devem ser registrados:

- Credenciais.
- Tokens de autenticação.
- Dados pessoais desnecessários.
- Conteúdo sensível de conversas sem justificativa.
- Informações que não sejam necessárias para diagnóstico ou auditoria.

O logging deve permitir identificar a origem de uma falha sem expor informações desnecessárias sobre o usuário ou o conteúdo de suas interações.

---

## 9. Regras gerais de integração

Para garantir a compatibilidade entre os componentes desenvolvidos pela equipe, devem ser observadas as seguintes regras:

1. Cada integrante deve respeitar as responsabilidades da camada pela qual é responsável.
2. Alterações em contratos compartilhados devem ser comunicadas aos integrantes envolvidos antes da integração.
3. Os nomes de arquivos, classes, funções e atributos devem seguir as convenções definidas no projeto.
4. Os tipos de entrada e saída devem ser explícitos sempre que possível.
5. Os modelos Pydantic devem ser utilizados para padronizar os dados que transitam entre as camadas.
6. Os serviços devem concentrar as regras de negócio determinísticas.
7. As tools devem permanecer como adaptadores entre agentes e serviços.
8. Os agentes especialistas devem receber somente o texto necessário à execução de suas chamadas, sem compartilhamento automático do histórico completo.
9. Os repositórios não devem acessar diretamente os caminhos físicos dos arquivos.
10. O acesso aos arquivos deve ocorrer por meio da abstração de armazenamento.
11. A ingestão e a recuperação documental devem respeitar os fluxos definidos para o RAG.
12. Os metadados das fontes documentais devem ser preservados durante todo o processo de recuperação.
13. O `chat_service` deve concentrar a integração com o ADK Runner e o gerenciamento das sessões.
14. Os serviços de domínio não devem depender dos agentes.
15. Nenhum componente deve assumir responsabilidades pertencentes a outra camada.
16. Mudanças em contratos devem ser refletidas na documentação e comunicadas aos responsáveis pelos módulos dependentes.

---

## 10. Decisões e alinhamentos pendentes

Os contratos estabelecem a estrutura de integração, mas alguns detalhes devem ser confirmados entre os responsáveis pelos módulos durante a implementação.

| Tema | Alinhamento necessário |
|---|---|
| Agentes especialistas | Confirmar os nomes, descrições e parâmetros das tools disponibilizadas a cada especialista. |
| Tools | Confirmar as funções e os parâmetros necessários para cada operação de negócio. |
| Services | Confirmar as assinaturas das funções e os modelos utilizados nas entradas e saídas. |
| Repositories | Confirmar os formatos de retorno e as operações de consulta disponibilizadas. |
| RAG | Confirmar o formato definitivo dos metadados e a disponibilidade da informação de página para cada tipo de documento. |
| Chat | Confirmar os tipos e nomes definitivos dos campos de requisição e resposta em `chat_model.py`. |
| Sessões | Definir os detalhes de criação, recuperação e encerramento das sessões no `chat_service`. |
| Erros | Alinhar as exceções específicas e os formatos de erro retornados pela API. |
| Logging | Confirmar os eventos e níveis de log necessários para cada componente. |

As decisões devem ser documentadas e incorporadas aos contratos quando forem confirmadas pelos responsáveis.

---

## 11. Considerações finais

Este documento deve funcionar como referência compartilhada para o desenvolvimento e a integração dos módulos do projeto.

A implementação dos componentes deve respeitar as responsabilidades estabelecidas na arquitetura, priorizando baixo acoplamento, separação de responsabilidades, rastreabilidade das informações e proteção dos dados.

Sempre que uma alteração exigir mudanças na comunicação entre dois ou mais componentes, os responsáveis devem alinhar o novo contrato antes de concluir a integração.

A arquitetura e os contratos devem evoluir de forma coordenada, mantendo `docs/ESTRUTURA.md` como referência para a organização dos componentes e este documento como referência para sua comunicação.