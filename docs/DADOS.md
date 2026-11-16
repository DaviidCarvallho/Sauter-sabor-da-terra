# Dicionário de dados — Sabor da Terra

Conferência dos seis arquivos estruturados fornecidos para o projeto (`produtores.csv`, `pedidos.json`, `financeiro.csv`, `sazonalidade.csv`, `tabela_precos_outubro_2026.csv`, `lotes.csv`).

**Responsável:** Arthur · tarefa 6.4 do `PLANO_DE_TAREFAS.md` (Dados e produtores) · **Base para:** `models/`, `repositories/`, `services/pedido_service`, `produtor_service` e `relatorio_service`.

Todos os números abaixo foram obtidos lendo os arquivos reais. Itens marcados como **Proposta** são decisões sugeridas, que dependem de confirmação da equipe (seção 9 do `PLANO_DE_TAREFAS.md`).

---

## 1. Visão geral

| Arquivo | Formato | Registros | Chave primária | Período / referência |
|---|---|---|---|---|
| `produtores.csv` | CSV, 16 colunas | 18 | `id` (`P001`…`P018`) | Cadastro atual |
| `financeiro.csv` | CSV, 17 colunas | 30 | `id_transacao` (`FIN-2026-001`…`030`) | Vendas de 02/09 a 25/10/2026; vencimentos até 09/12/2026 |
| `lotes.csv` | CSV, 14 colunas | 20 | `lote_id` (`LOT-2026-0089`…`0108`) | Entregas de 02/09 a 25/10/2026 |
| `sazonalidade.csv` | CSV, 14 colunas | 50 produtos | `produto` | Calendário anual (jan–dez) |
| `tabela_precos_outubro_2026.csv` | CSV, 7 colunas | 53 linhas | `produto` | Preços vigentes em outubro/2026 |
| `pedidos.json` | JSON (lista de objetos), 7 campos | 15 | `id` (`PED-2026-001`…`015`) | Recebidos de 28 a 30/10/2026 |

### Formato técnico comum

| Aspecto | Valor encontrado |
|---|---|
| Codificação | UTF-8, sem BOM |
| Fim de linha | LF (sem CRLF) |
| Separador CSV | vírgula (`,`) |
| Campos com vírgula | Entre aspas duplas (ex.: `endereco`, `produtos`, `observacao`). Use o módulo `csv`, nunca `split(",")` |
| Separador decimal | Ponto (`4.50`), sem separador de milhar |
| Data | ISO 8601: `AAAA-MM-DD` |
| Data e hora (só em `pedidos.json`) | `AAAA-MM-DDTHH:MM:SS`, sem fuso horário |
| Valor vazio | Texto vazio (`,,`). Ocorre em `validade_certificacao`, `data_pagamento` e `observacao` |
| Valor "não se aplica" | `n/d` (só nos preços). `ambiente` (só em `temperatura_transporte_c`) |
| Cabeçalho | Sempre presente, em `snake_case` sem acento |
| Acentos | Presentes nos valores (`maracujá`, `rúcula`, `mel de jandaíra`) e **ausentes** nos nomes de coluna |

> **Armadilha de tipagem:** `cpf`, `telefone`, `agencia` e `conta_corrente` devem ser lidos como **texto**. A agência `0437` e a conta `0073921-7` perdem o zero à esquerda se forem convertidas para número.

---

## 2. `produtores.csv`

18 produtores: 17 `ativo`, 1 `inativo` (P015). 9 com certificação orgânica e 9 sem. 7 municípios (Garanhuns 7, Caetés 2, Jucati 2, Lajedo 2, Águas Belas 2, Bom Conselho 2, Brejão 1).

| Coluna | Tipo sugerido | Formato / exemplo | Observações |
|---|---|---|---|
| `id` | `str` | `P001` | Único. Identificador usado em todos os outros arquivos |
| `nome_completo` | `str` | `Maria das Graças Silva Ferreira` | |
| `cpf` | `str` | `831.452.674-90` | Sempre com pontos e hífen. **Dado pessoal** |
| `data_nascimento` | `date` | `1975-03-12` | **Dado pessoal** |
| `telefone` | `str` | `(87) 99812-3456` | Formato `(DD) 9NNNN-NNNN`. Coincide com o `remetente` de `PED-2026-012` e `015` |
| `email` | `str` | `maria.graca@email.com` | |
| `endereco` | `str` | `Sítio Boa Vista, Zona Rural s/n` | Texto livre, com vírgulas |
| `municipio` | `str` | `Garanhuns` | 7 valores distintos |
| `produtos` | `list[str]` | `goiaba,acerola,manga` | **Lista separada por vírgula dentro de uma célula**, em minúsculas. Precisa de `split(",")` e `strip()` |
| `certificacao_organica` | `bool` | `sim` / `nao` | Só esses dois valores (sem acento em `nao`) |
| `validade_certificacao` | `date \| None` | `2027-06-15` | Vazio quando `certificacao_organica = nao`. Todos os 9 certificados têm data |
| `chave_pix` | `str` | CPF, e-mail ou telefone | 12 são CPF, 4 telefone, 2 e-mail. Sempre igual a um dos três campos do próprio produtor |
| `banco` | `str` | `Banco do Brasil` | 7 bancos distintos |
| `agencia` | `str` | `0437` | Preservar zeros à esquerda |
| `conta_corrente` | `str` | `28901-3` | Tamanhos variados, com dígito após hífen |
| `status` | `Literal["ativo","inativo"]` | `ativo` | |

**Situação das certificações (nada a inferir, está nos dados):**

- **P008 (Josefa): vencida desde 30/09/2026.** É o caso citado no `LEIA-ME.txt`.
- **P004 (Ana Lúcia): vence em 01/12/2026.** Está vigente, mas faltam poucas semanas.
- Os outros 7 certificados vencem entre 01/2027 e 08/2027.

---

## 3. `financeiro.csv`

30 transações, todas com `tipo = venda`. Total vendido: **R$ 24.634,00**. 20 `pago`, 10 `pendente` (R$ 13.380,00 a receber).

| Coluna | Tipo sugerido | Formato / exemplo | Observações |
|---|---|---|---|
| `id_transacao` | `str` | `FIN-2026-001` | Único |
| `data` | `date` | `2026-09-02` | Data da venda |
| `produtor_id` | `str` | `P001` | FK para `produtores.id`. Todos existem |
| `produtor_nome` | `str` | | **Denormalizado.** Igual ao cadastro nas 30 linhas |
| `produtor_cpf` | `str` | | **Denormalizado.** Igual ao cadastro nas 30 linhas |
| `comprador` | `str` | `Mercado Bom Preço` | Texto livre. Não existe cadastro de compradores nem ID. 10 valores distintos |
| `tipo` | `str` | `venda` | Único valor presente. Não há estorno, adiantamento nem outra natureza |
| `produto` | `str` | `goiaba paluma` | Ver seção 7 (nomes de produto) |
| `quantidade_kg` | `Decimal` | `120` | **O nome engana: nem sempre é kg.** Ver seção 6 |
| `valor_unitario` | `Decimal` | `4.50` | Preço por unidade de medida do produto |
| `valor_total` | `Decimal` | `540.00` | Confere com `quantidade × valor_unitario` nas 30 linhas |
| `forma_pagamento` | `str` | `boleto 30 dias` | Valores: `boleto 30 dias` (13), `pix` (10), `empenho 45 dias` (5), `transferência` (2) |
| `status_pagamento` | `Literal["pago","pendente"]` | | **Não existe o valor "atrasado"**. Ver seção 5 |
| `data_vencimento` | `date` | `2026-10-02` | Sempre preenchida |
| `data_pagamento` | `date \| None` | `2026-10-01` | Vazia em todas as `pendente`. Preenchida em todas as `pago` |
| `chave_pix_deposito` | `str` | | **Denormalizado.** Igual à `chave_pix` do cadastro nas 30 linhas. **Dado pessoal** |
| `observacao` | `str` | `Empenho 2026NE00234` | Texto livre. Carrega o número do empenho, avisos de atraso e a unidade de medida (ex.: `Preço por dúzia`) |

**Fatos úteis para o `relatorio_service`:**

- 17 dos 18 produtores têm transações. **P015 (inativo) não tem nenhuma.** É o caso de "produtor sem transações" (decisão 7 da seção 13).
- Quatro transações foram pagas depois do vencimento: `FIN-2026-008` e `009` (2 dias), `018` e `019` (1 dia). O status continua `pago`.
- Três transações dividem o mesmo empenho (`2026NE00234`: `FIN-005`, `006`, `007`). A `005` é de P002 e a `006` e `007` são de P004.

---

## 4. `lotes.csv`

20 lotes entregues de 02/09 a 25/10/2026. Todos com `inspecao_visual = aprovado`.

| Coluna | Tipo sugerido | Formato / exemplo | Observações |
|---|---|---|---|
| `lote_id` | `str` | `LOT-2026-0089` | Único, sequencial |
| `data_colheita` | `date` | `2026-09-01` | Nunca posterior à entrega |
| `data_entrega` | `date` | `2026-09-02` | |
| `produtor_id` | `str` | `P003` | FK para `produtores.id` |
| `produtor_nome`, `produtor_cpf` | `str` | | Denormalizados. Iguais ao cadastro nas 20 linhas |
| `produto` | `str` | `queijo coalho` | |
| `quantidade_kg` | `Decimal` | `45` | Mesma ressalva de unidade do financeiro |
| `comprador` | `str` | `Restaurante Raízes` | Texto livre |
| `pedido_id` | `str` | `PED-2026-SEP-003` | **Não bate com `pedidos.json`.** Ver seção 8 |
| `temperatura_transporte_c` | `int \| Literal["ambiente"]` | `8` ou `ambiente` | **Coluna mista.** 11 são `ambiente`, 9 são número inteiro (4 a 12 °C) |
| `validade` | `date` | `2026-10-02` | Nunca anterior à entrega |
| `inspecao_visual` | `str` | `aprovado` | Único valor presente |
| `observacao` | `str` | `Certificação orgânica anexa` | Texto livre. Também carrega a unidade (`300 unidades`) |

**Relação com o financeiro:** os 20 lotes têm uma transação correspondente (mesmo produtor, produto e quantidade), mas 10 das 30 transações não têm lote (`FIN-010`, `015`, `017`, `019`, `020`, `022`, `023`, `025`, `026`, `029`). Não há coluna que ligue os dois. Em 2 casos (`LOT-0089` e `0090`) a data da transação é 3 dias depois da entrega (`FIN-003` e `004`: 05/09, contra 02/09).

---

## 5. Pendências financeiras: regra de cálculo

O arquivo só tem `pago` e `pendente`. "Atrasado" é **calculado**, comparando `data_vencimento` com uma **data de referência**. A escolha da data muda o resultado:

| Data de referência | Pendentes vencidos | Valor |
|---|---|---|
| 30/10/2026 (último pedido do conjunto) | 5 (`005`, `006`, `007`, `013`, `014`) | R$ 8.690,00 |
| 14/11/2026 | 8 (as 5 acima, mais `023`, `024`, `025`) | R$ 10.500,00 |

Há também uma sinalização manual: `observacao = "ATRASADO - cobrar"` em `FIN-013` e `014`. Ela não cobre as outras pendentes vencidas e não deve ser usada como regra.

**Proposta:**

- Pendência = `status_pagamento == "pendente"`.
- Em atraso = pendência com `data_vencimento < data_referencia`.
- A data de referência é parâmetro de entrada do `relatorio_service` (padrão: `date.today()`), para os testes ficarem determinísticos.
- Valores em `Decimal`, nunca `float`.

---

## 6. Unidades de medida

A coluna se chama `quantidade_kg` em `financeiro.csv` e `lotes.csv`, mas guarda a quantidade **na unidade do produto**, definida em `tabela_precos_outubro_2026.csv`. Casos confirmados:

| Produto | Unidade real | Onde aparece | Evidência |
|---|---|---|---|
| `alface` | unidade | `FIN-006`, `FIN-011`, `LOT-0094`, `LOT-0098` | Lote: `300 unidades`, `80 unidades` |
| `coentro` | maço | `FIN-007`, `LOT-0095` | Lote: `150 maços` |
| `couve` | maço | `FIN-012`, `LOT-0099` | Lote: `40 maços (kg)`, com a anotação contraditória "(kg)" |
| `ovos caipira` | dúzia | `FIN-019` | Observação: `Preço por dúzia` |

Unidades que existem na tabela de preços: `kg` (40 linhas), `maço` (7), `litro` (3), `unidade` (2), `dúzia` (1).

Outra armadilha: `volume_minimo_atacado_kg` tem "kg" no nome, mas também usa a unidade do produto (ex.: `alface`, 50 **unidades**; `coentro`, 50 **maços**; `ovos caipira`, 50 **dúzias**).

**Proposta:** nos models, nomear o campo `quantidade` e carregar a `unidade` junto, resolvida pelo `produto_repository`. Nunca somar `quantidade_kg` de produtos diferentes sem converter ou agrupar por unidade.

---

## 7. Nomes de produto: não são consistentes entre arquivos

Os cinco arquivos usam nomes diferentes para o mesmo produto. Um join por texto exato **falha**.

| Cadastro (`produtores.produtos`) | `sazonalidade.csv` | `tabela_precos` | Observação |
|---|---|---|---|
| `goiaba` | `goiaba paluma` | `goiaba paluma extra` e `goiaba paluma especial` | Duas variedades de preço, uma de sazonalidade |
| `manga` | `manga tommy` | `manga tommy` | |
| `banana` | `banana prata` | `banana prata` | |
| `tomate` | `tomate` | `tomate santa cruz` | |
| `tomate cereja` | **`tomate`** | `tomate cereja` | Só P004 produz |
| `pimentão` | `pimentão` | `pimentão verde` e `pimentão colorido` | |
| `mel de abelha jandaíra` | `mel de jandaíra` | `mel de jandaíra` | Só P002 |
| `tapioca` e `goma` (P013, itens separados) | `tapioca/goma` (um item só) | `tapioca/goma` | |
| `feijão`, `milho`, `fava` (P015, inativo) | **ausentes** | **ausentes** | Sem safra nem preço |

O `financeiro.csv` e o `lotes.csv` usam os nomes da sazonalidade. Entre eles, `goiaba paluma`, `tomate` e `pimentão` não existem como linha exata na tabela de preços.

**Proposta:** o `produto_repository` mantém um mapa de normalização explícito e testado (nome de cadastro → nome de sazonalidade → linhas de preço). Não usar busca por prefixo, que erra em `tomate` e `tomate cereja`. Nomes sem correspondência devem devolver "produto não encontrado" e nunca um valor presumido.

---

## 8. `pedidos.json`

Lista de 15 objetos, todos com os mesmos 7 campos. **Não existem campos de tipo, urgência, itens, quantidades ou prazo.** Tudo isso está dentro do texto livre de `mensagem_original` e precisa ser extraído pelo agente (do David) e validado pelo `pedido_service`.

| Campo | Tipo sugerido | Exemplo | Observações |
|---|---|---|---|
| `id` | `str` | `PED-2026-001` | Único |
| `data_recebimento` | `datetime` | `2026-10-28T09:15:00` | Sem fuso horário. **É a âncora para datas relativas** ("sexta", "amanhã", "hoje") |
| `canal` | `Literal["email","whatsapp","formulario_web"]` | | 6 e-mails, 6 WhatsApp, 3 formulários |
| `remetente` | `str` | | **Formato misto**: e-mail (6), telefone (6) ou nome da empresa (3). Em `012` e `015`, o telefone é o de um produtor cadastrado (P001 e P003) |
| `comprador` | `str` | `Dona Cremilda - Lanchonete da Feira` | Texto livre. Nome diferente do usado no financeiro (ver abaixo) |
| `mensagem_original` | `str` | | Texto livre, com `\n`. Pode estar em inglês (`PED-011`), sem pontuação e com abreviações (`PED-003`, `005`) |
| `status` | `str` | `pendente` | Único valor presente |

**Leitura preliminar dos 15 pedidos** (para validar com o David antes de fixar o vocabulário de tipo e urgência):

| Natureza | Pedidos |
|---|---|
| Pedido de compra com itens e quantidades | `001`, `002`, `003`, `004`, `005`, `006`, `007` |
| Cotação, orçamento ou consulta de fornecimento | `008`, `009`, `010`, `011` (em inglês), `013` |
| Solicitação de produtor | `012` (P001: vendas e saldo a receber), `015` (P003: oferta de estoque e indicação de novo produtor) |
| Notificação oficial | `014` (ADAGRO: inspeção em 11 e 12/11) |

**Datas que não fecham com o calendário (confirmado):**

| Pedido | Texto | Problema |
|---|---|---|
| `PED-2026-001` | "essa sexta **(01/nov)**" | 01/11/2026 é **domingo**. A sexta seguinte ao recebimento (qua 28/10) é 30/10 |
| `PED-2026-002` | "terça **04/nov**" | 04/11/2026 é **quarta-feira**. A terça é 03/11 |

O agente não deve escolher uma das duas datas em silêncio: deve sinalizar a divergência. O código pode detectar isso comparando o dia da semana citado com a data explícita.

**Exemplos do que o código precisa verificar:** `PED-004` e `PED-009` exigem certificação orgânica; `PED-006` pede 200 kg de queijo coalho, 50 kg de queijo manteiga, 40 kg de mel orgânico e 300 kg de goiaba **no mesmo dia**; `PED-007` pede `cajá`, que em novembro está em safra `baixa`.

**Nomes de comprador diferem entre arquivos** (sem ID de comprador, qualquer ligação é por nome):

| `pedidos.json` | `financeiro.csv` |
|---|---|
| `SESC - Unidade Garanhuns` | `SESC Garanhuns` |
| `Dona Cremilda - Lanchonete da Feira` | `Lanchonete da Feira` |
| `Marcos - Sorveteria Tropical` | `Sorveteria Tropical` |
| `João Pedro - Feira Orgânica do Recife` | `Feira Orgânica do Recife` |

**IDs de pedido: dois formatos que não se encontram.**

- `pedidos.json`: `PED-2026-001` a `015` (numeração simples).
- `lotes.csv`: `PED-2026-SEP-003`, `PED-2026-OCT-012` (mês abreviado + sequência).
- Nenhum `pedido_id` dos lotes existe em `pedidos.json`. Os lotes são de entregas anteriores (set–out) e os pedidos do JSON são novos (28–30/10). **A rastreabilidade por `pedido_id` não pode ser usada para ligar os dois arquivos.**

---

## 9. `sazonalidade.csv`

50 produtos, uma linha por produto, uma coluna por mês.

| Coluna | Tipo sugerido | Observações |
|---|---|---|
| `produto` | `str` | Chave. Ver seção 7 |
| `jan` … `dez` | `Literal["alta","media","baixa","nenhuma"]` | Nomes de mês em 3 letras minúsculas, **sem acento** (`media`, não `média`). Ordem do calendário. Contagem: `alta` 416, `media` 127, `nenhuma` 36, `baixa` 21 |
| `observacao` | `str` | Texto livre, pode estar vazio. Contém regras que **não estão nas colunas**, como "~80kg/semana" |

**Para novembro** (mês de referência dos pedidos): `umbu`, `mirtilo` e `framboesa` são `nenhuma`; `cajá` é `baixa`.

**Capacidade de produção: não existe como dado estruturado.** Nenhum arquivo tem coluna de capacidade por produtor. As únicas pistas são:

- `sazonalidade.observacao`: `frango caipira` "escala limitada a ~80kg/semana"; `ovos caipira` "~120 dúzias/semana".
- `tabela_precos.observacao`: exclusividade por produtor em texto livre ("Apenas P003", "Apenas P018", "P017 sem SIE").
- O histórico de lotes e vendas dá uma ordem de grandeza, mas não um limite.

O plano de tarefas manda sinalizar "quantidade acima da capacidade". Sem esse dado, a regra precisa ser **definida pela equipe** (ver seção 13, decisão 2). Algumas escolhas possíveis: usar só os limites explícitos das observações; usar o maior volume já entregue por produto; ou aceitar que o sistema só alerta onde o dado existe.

**Inconsistência menor:** `tomate` tem observação "dois picos: jun-jul e out-jan", mas jun está `media` e jul `alta`.

---

## 10. `tabela_precos_outubro_2026.csv`

53 linhas (mais linhas que a sazonalidade, porque algumas variedades têm preço próprio).

| Coluna | Tipo sugerido | Observações |
|---|---|---|
| `produto` | `str` | Único. Ver seção 7 |
| `unidade` | `Literal["kg","unidade","maço","litro","dúzia"]` | Ver seção 6 |
| `preco_convencional` | `Decimal \| None` | `n/d` em 4 produtos (`mel de jandaíra`, `própolis`, `pólen`, `cera de abelha`, que só existem como orgânicos) |
| `preco_organico` | `Decimal \| None` | `n/d` em 19 produtos. Converter para `None` |
| `desconto_atacado_pct` | `int` | Percentual inteiro (`10` = 10%). `0` = sem desconto |
| `volume_minimo_atacado_kg` | `int` | Na unidade do produto, não em kg. `0` = sem atacado. Em 16 linhas desconto e volume são ambos `0` |
| `observacao` | `str` | Texto livre. Contém restrições importantes: "Apenas P003", "sem SIE para revenda", "venda direta apenas" |

**Pontos de atenção:**

- **`leite`:** tem preço orgânico (R$ 5,50), mas o único produtor (P011) não é certificado. Inconsistência dentro do dado.
- **`frango caipira` e `iogurte natural`:** a observação diz que **não têm SIE** (inspeção estadual): venda direta apenas, sem revenda. É uma restrição de negócio escrita em texto livre. Só aparece nessa coluna, então o `pedido_service` deveria tratá-la como regra explícita.
- **Preço histórico x tabela:** o `valor_unitario` do financeiro é o praticado no dia da venda e pode diferir da tabela (ex.: queijo coalho vendido a R$ 30,00, R$ 31,00, R$ 32,00 e R$ 33,00, contra R$ 32,00 na tabela). Não usar a tabela para recalcular o histórico.

---

## 11. Mapa de relacionamentos

```text
produtores.id (P001…P018)
   ├── financeiro.produtor_id        (30 transações; P015 sem nenhuma)
   ├── lotes.produtor_id             (20 lotes)
   └── "Apenas P0xx" em tabela_precos.observacao   (texto livre, não é FK)

produtores.produtos ──(nome, ver seção 7)──► sazonalidade.produto ──► tabela_precos.produto
financeiro.produto, lotes.produto ──(nome)──► sazonalidade.produto

lotes.pedido_id      ✗  não liga a pedidos.json
financeiro ↔ lotes   sem chave comum (os 20 lotes casam com uma transação por produtor+produto+quantidade; 10 transações não têm lote)
comprador            texto livre nos três arquivos, com grafias diferentes
```

**Resumo:** a única chave que funciona de forma confiável entre arquivos é `produtor_id`. Todo o resto (produto, comprador, pedido) depende de normalização ou de decisão da equipe.

---

## 12. Dados pessoais e sensíveis

Os arquivos contêm dados que o assistente **não deve devolver no chat sem necessidade**:

| Onde | Dado |
|---|---|
| `produtores.csv` | `cpf`, `data_nascimento`, `telefone`, `email`, `endereco`, `chave_pix`, `banco`, `agencia`, `conta_corrente` |
| `financeiro.csv` | `produtor_cpf`, `chave_pix_deposito` |
| `lotes.csv` | `produtor_cpf` |
| `pedidos.json` | CPF/RG de terceiros (`004`, `013`, `015`), CNPJ, conta bancária de P001 citada em `012` |

**Proposta:** os models usados pelas tools do agente não carregam `cpf`, dados bancários nem data de nascimento. Se algum caso exigir, entregar o dado mascarado (`***.452.674-**`). O dado completo fica só no model interno do repositório. Isso também atende ao critério de aceite de segurança do plano.

---

## 13. Decisões que dependem da equipe

| # | Decisão | Quem decide com Arthur | Proposta |
|---|---|---|---|
| 1 | Data de referência para "atraso" e para validade de certificação | Murilão | Parâmetro do serviço, padrão `date.today()`, fixa nos testes |
| 2 | Regra de capacidade (não há dado) | David | Definir fonte: limites explícitos nas observações, ou maior volume histórico, ou alertar só onde há dado |
| 3 | Vocabulário de `tipo` e `urgência` do pedido | David | Partir da leitura da seção 8, e fechar depois de testar nos 15 pedidos |
| 4 | Mapa de normalização de nomes de produto | David | Arquivo único no `produto_repository`, com testes (seção 7) |
| 5 | Unidade das quantidades | David, Rawan | Campo `quantidade` + `unidade` (seção 6) |
| 6 | Ligação lote ↔ pedido | Rawan, David | Não depender de `pedido_id`; ligar por produtor + produto + data |
| 7 | Produtor sem transações (P015) | Murilão | Relatório devolve zero vendas e nenhuma pendência, e informa que o produtor está inativo |
| 8 | Dados pessoais nas respostas do agente | Murilão | Models públicos sem CPF e dados bancários (seção 12) |
| 9 | Certificação vencida ou prestes a vencer | Rawan, David | Considerar inválida `validade < referência`. Alertar vencimento em até 60 dias |

---

## 14. Resumo das anomalias encontradas

| # | Achado | Impacto |
|---|---|---|
| 1 | `quantidade_kg` guarda unidades, maços e dúzias em alguns produtos | Somas e relatórios errados se tratadas como kg |
| 2 | Nomes de produto diferentes entre cadastro, sazonalidade, preços, financeiro e lotes | Join por texto falha; alertas de safra e preço ficam errados |
| 3 | Não existe dado de capacidade por produtor | A regra "quantidade acima da capacidade" precisa ser definida |
| 4 | `lotes.pedido_id` não corresponde a nenhum `pedidos.json.id` | Rastreabilidade por pedido impossível |
| 5 | Datas explícitas que contradizem o dia da semana (`PED-001`, `PED-002`) | Agente deve sinalizar, não adivinhar |
| 6 | Atraso não é status: depende de uma data de referência | Resultado do relatório muda conforme a data usada |
| 7 | P008 com certificação vencida em 30/09 e lote `LOT-2026-0104` entregue em 01/10 com a observação "Certificação orgânica anexa" | Possível problema de conformidade nos dados, útil para teste de rastreabilidade |
| 8 | `leite` com preço orgânico, mas o único produtor não é certificado | Inconsistência no preço |
| 9 | `temperatura_transporte_c` mistura número e o texto `ambiente` | Parsing precisa de tipo união |
| 10 | `lotes.observacao` de `LOT-0099`: `40 maços (kg)` | Unidade contraditória |
| 11 | `n/d` como valor ausente nos preços | Converter para `None` ao ler |
| 12 | Cadastro de P015 (inativo) lista `feijão`, `milho`, `fava` sem sazonalidade nem preço | Produto sem dado de apoio |