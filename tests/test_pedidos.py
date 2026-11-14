"""Testes de triagem de pedidos.

Casos previstos (Fase 4 (orquestrador, Agente de Pedidos e API de chat)):
- Produto fora de safra gera alerta
- Quantidade acima da capacidade dos produtores gera alerta
- Pedido incompleto lista as informações ausentes
- Pedido coloquial ('30kg de queijo coalho e umas caixas de goiaba pra sexta') tem a quantidade ambígua sinalizada
- Urgência é classificada de acordo com o prazo
"""

import pytest

pytestmark = pytest.mark.skip(reason="Esqueleto: implementar junto com a Fase 4 (orquestrador, Agente de Pedidos e API de chat)")


def test_pendente():
    ...
