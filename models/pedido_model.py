"""Schemas de pedidos.

Função:
    Representa um pedido bruto (texto livre) e o pedido estruturado após a triagem.

Responsabilidades:
    - Pedido estruturado: itens (produto, quantidade, unidade), prazo, comprador, tipo e urgência
    - Informações ausentes ou ambíguas e alertas (fora de safra, quantidade acima da capacidade)

Não deve:
    - Inventar valores para 'tipo' ou 'urgência' antes de analisar o pedidos.json

Relações:
    Usa:        pydantic
    Usado por:  services.pedido_service, repositories.pedido_repository, agents.tools

Observação:
    Os campos seguem o item 4.1 do enunciado. Os valores possíveis de tipo e urgência serão definidos a partir dos dados reais.

Status: parcial (Fase 3): PedidoBruto (registro de pedidos.json) implementado.
    O pedido estruturado (itens, tipo, urgência, alertas) será definido com o David
    depois de fechado o vocabulário de tipo e urgência.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PedidoBruto(BaseModel):
    """Pedido exatamente como chega em pedidos.json (texto livre, sem interpretação).

    O arquivo não traz tipo, urgência, itens nem produtor: isso é extraído do texto pelo
    agente e validado pelo pedido_service. 'data_recebimento' é a data de referência para
    expressões relativas do texto ("sexta", "amanhã", "hoje").
    """

    model_config = ConfigDict(frozen=True)

    id: str
    data_recebimento: datetime
    canal: Literal["email", "whatsapp", "formulario_web"]
    # E-mail, telefone ou nome da empresa, dependendo do canal.
    remetente: str
    comprador: str
    mensagem_original: str
    status: str