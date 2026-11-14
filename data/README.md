# Pasta `data/`

Dados e documentos da Cooperativa Sabor da Terra. **Todos fictícios**, fornecidos no enunciado do projeto.

Esta pasta é lida **somente através da interface `Storage`** (`storage/`). Nenhum agente ou serviço usa caminhos desta pasta diretamente.

## Arquivos esperados

| Arquivo / pasta | Conteúdo (conforme o enunciado) | Quem lê | Situação |
|---|---|---|---|
| `produtores.csv` | Cadastro dos 18 produtores, com produtos e certificações | `produtor_repository` | Aguardando envio |
| `pedidos.json` | 15 pedidos em linguagem natural variada | `pedido_repository` | Aguardando envio |
| `financeiro.csv` | Transações financeiras (set-out/2026) | `financeiro_repository` | Aguardando envio |
| `sazonalidade.csv` | Disponibilidade dos produtos por mês | `produto_repository` | Aguardando envio |
| `tabela_precos_outubro_2026.csv` | Preços vigentes, convencional e orgânico | `produto_repository` | Aguardando envio |
| `lotes.csv` | Rastreabilidade dos últimos lotes entregues | `lote_repository` | Aguardando envio |
| `certificacoes/` | Certificações orgânicas, laudos sanitários e inspeção ADAGRO | `document_repository` (RAG) | Aguardando envio |
| `contratos/` | Contratos com Mercado Bom Preço, PNAE e Restaurante Raízes | `document_repository` (RAG) | Aguardando envio |
| `fichas_tecnicas/` | Fichas de queijo coalho, mel, goiaba, hortaliças e tubérculos | `document_repository` (RAG) | Aguardando envio |

## Regras

- Não inventar nem editar dados: o que está aqui é a fonte de verdade do protótipo.
- Os esquemas (colunas e campos) dos modelos em `models/` serão definidos a partir destes arquivos reais.
- Para trocar o armazenamento por nuvem no futuro, basta usar a mesma estrutura de pastas e nomes dentro de um bucket (`STORAGE_BACKEND=gcs`).
