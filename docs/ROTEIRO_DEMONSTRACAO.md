# Roteiro da demonstração (10 minutos)

Roteiro para a apresentação de 20 e 21/11/2026. Todas as mensagens abaixo foram executadas com o Gemini real em 19/11/2026 (a do pedido incompleto e a do P001 em variações próximas, ver `docs/AGENTES_E_TRIAGEM.md`, seção 9) e o comportamento descrito é o que se observou; o texto exato do modelo varia a cada execução.

## Antes de começar

1. `.env` com `GOOGLE_API_KEY` válida (nunca mostrar o arquivo na tela).
2. Índice construído nesta máquina: `python -m rag.ingestion` (cerca de 20 s, usa a API de embeddings). Sem ele, as perguntas documentais respondem "evidência insuficiente".
3. Servidor no ar: `uvicorn main:app --reload` e abrir http://127.0.0.1:8000.
4. **Cota:** o Free Tier aceita cerca de 15 requisições por minuto e cada mensagem usa de 3 a 6. Espere cerca de 30 segundos entre as mensagens. Se aparecer o aviso de limite (429), aguarde 1 minuto e repita.
5. Se aparecer falha 502 isolada, é instabilidade do modelo ("alta demanda"): repita a mensagem.
6. Os pedidos de `data/pedidos.json` são de 28 a 30/10/2026. Para a triagem fazer sentido com datas relativas, use mensagens com data explícita (como abaixo) ou avise que "hoje" é a data real do computador.

## Sequência

| Tempo | Cena | Mensagem | O que mostrar |
|---|---|---|---|
| 0:00 | Abertura | — | O problema (60 a 100 pedidos por dia em texto livre) e a regra central: o modelo interpreta, o código verifica |
| 1:30 | Triagem completa | `O Restaurante Raízes precisa de 30kg de queijo coalho e 10kg de manteiga de garrafa para o dia 25/11/2026.` | Agente "Pedidos" acionado, valores, produtores elegíveis, urgência e tipo |
| 3:00 | Alertas do código | `Preciso de 50 kg de mirtilo orgânico para o dia 25/11/2026. Sou a Sorveteria Tropical.` | Alerta de **fora de safra** (mirtilo: maio a setembro) em destaque: vem do código, não do modelo |
| 4:30 | Pedido incompleto | `Quero 30kg de queijo coalho e umas caixas de goiaba pra sexta. Aqui é o Restaurante Raízes.` | O sistema não inventa a quantidade de caixas: pergunta |
| 5:30 | Documentos com fonte | `Quais produtores têm certificação orgânica vigente para mel?` | Resposta com os produtores, validade e a lista de fontes (arquivo) |
| 6:30 | Sem evidência | `O contrato com o Supermercado Extra prevê quais condições de devolução de produtos?` | "Não encontrei essa informação": o assistente não inventa |
| 7:30 | Produtor | `Faça um resumo do produtor P001 (Maria das Graças) com vendas, pedidos e pendências.` | Totais vindos dos dados, não do modelo |
| 8:30 | Salvaguarda | `Quanto eu vendi esse mês? Sou a produtora Maria.` | Nenhum especialista acionado; o assistente orienta procurar a equipe |
| 9:00 | Arquitetura e limites | — | `docs/ARQUITETURA_E_DECISOES_TECNICAS.md`: camadas, o que é planejado (GCS, persistência, autenticação) e o que ainda falta |

## O que não prometer

- O assistente **não registra nem confirma pedidos** e não envia notificações: só tria e redige.
- Não há autenticação; a recusa de consultas pessoais de produtores é uma salvaguarda do prompt, não controle de acesso.
- Sessões ficam na memória do servidor: reiniciar apaga a conversa.
- A qualidade foi verificada manualmente, com uma execução por caso (ver `docs/AGENTES_E_TRIAGEM.md`, seção 9).

## Plano B

- API fora do ar ou sem cota: mostrar os testes (`pytest` com `GOOGLE_API_KEY` vazia roda sem a API) e o conteúdo de `evals/`.
- Sem o índice: pular as cenas 5 e 6 e explicar que a ingestão é um processo separado.
