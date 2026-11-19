# Teste de usabilidade do chat — Sabor da Terra

Objetivo: descobrir se a interface é intuitiva para quem nunca a viu. Faça com **3 ou 4 pessoas** (colegas, alguém de fora da área). Uma pessoa de cada vez.

## Como conduzir
1. Abra a tela (`python qa/mock_server.py` e http://127.0.0.1:8001, ou o projeto real em http://127.0.0.1:8000).
2. Diga só: "Esta é a tela de um assistente de uma cooperativa agrícola. Faça as tarefas que eu pedir. Não vou ajudar; se travar, fale em voz alta o que está pensando."
3. Entregue uma tarefa por vez, **sem explicar onde clicar**.
4. Anote o tempo, os cliques errados e o que a pessoa disse. Não corrija nem dê dicas.

## Tarefas
| # | Tarefa dada à pessoa | Sucesso se… |
|---|---|---|
| 1 | "Registre um pedido de 40 kg de morango." | Envia a mensagem sem ajuda |
| 2 | "Descubra quais produtores têm certificação orgânica para mel e de qual documento isso veio." | Acha as **fontes** na resposta |
| 3 | "Este pedido tem algum problema? Como você sabe?" | Percebe os **alertas** sem ser apontada |
| 4 | "Aconteceu um erro. O que você faria?" (use `erro500` na mensagem) | Entende o aviso e usa **Tentar de novo** |
| 5 | "Comece uma conversa do zero." | Acha **Nova conversa** |

## Registro (copie uma tabela por pessoa)
Pessoa: ______  Data: ______  Dispositivo: computador / celular

| Tarefa | Conseguiu sozinha? (S/N) | Tempo | Onde hesitou ou clicou errado | Frase dita |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

## Perguntas ao final (nota de 1 a 5, sendo 5 = concordo totalmente)
1. Foi fácil entender o que escrever.
2. Entendi de onde vêm as informações da resposta.
3. Entendi quando havia um alerta ou problema.
4. Se der erro, sei o que fazer.
5. Usaria no dia a dia.

E uma aberta: **"O que você mudaria primeiro?"**

## Como usar o resultado
- Qualquer tarefa que mais da metade das pessoas não conseguiu sozinha vira item de melhoria prioritário.
- Médias abaixo de 4 nas perguntas 1 a 4 indicam texto, rótulo ou posição a ajustar.
- Registre as melhorias feitas e anexe as anotações como evidência de QA.
