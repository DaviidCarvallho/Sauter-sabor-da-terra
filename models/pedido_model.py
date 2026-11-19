"""Schemas de pedidos.

Função:
    Representa um pedido bruto (texto livre) e o pedido estruturado após a triagem.

Responsabilidades:
    - Pedido bruto: registro exatamente como chega em pedidos.json
    - Pedido estruturado (parte factual/determinística): itens solicitados, itens validados,
      produtores elegíveis, valores estimados, informações ausentes e alertas calculados em código
    - Manter 'tipo' e 'urgencia' abertos (str | None) até alinhamento do vocabulário com David

Não deve:
    - Inventar enum fechado para 'tipo' ou 'urgencia' antes de fechar com David
    - Conter lógica de negócio ou acesso a arquivos

Relações:
    Usa:        pydantic, models.produto_model
    Usado por:  services.pedido_service, repositories.pedido_repository, agents.tools
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.produto_model import NivelSafra

NivelSeveridade = Literal["alta", "media", "info"]

TipoAlertaTriagem = Literal[
    "fora_de_safra",
    "baixa_disponibilidade",
    "quantidade_acima_capacidade",
    "restricao_sanitaria_sie",
    "exclusividade_produtor",
    "certificacao_organica_indisponivel",
    "certificacao_vencida",
    "unidade_divergente",
    "data_inconsistente",
    "produto_nao_encontrado",
    "informacao_ausente",
]


class PedidoBruto(BaseModel):
    """Pedido exatamente como chega em pedidos.json (texto livre, sem interpretação)."""

    model_config = ConfigDict(frozen=True)

    id: str
    data_recebimento: datetime
    canal: Literal["email", "whatsapp", "formulario_web"]
    remetente: str
    comprador: str
    mensagem_original: str
    status: str


class AlertaTriagem(BaseModel):
    """Alerta determinístico produzido pelo código na validação do pedido."""

    model_config = ConfigDict(frozen=True)

    tipo: TipoAlertaTriagem
    mensagem: str
    severidade: NivelSeveridade
    produto: str | None = None


class ItemPedidoEntrada(BaseModel):
    """Item extraído de um pedido antes da validação determinística."""

    model_config = ConfigDict(frozen=True)

    produto_informado: str
    quantidade: Decimal | None = Field(default=None, gt=0)
    unidade_informada: str | None = None
    organico: bool = False


class ProdutorElegivel(BaseModel):
    """Dados públicos do produtor elegível para atender a um item (sem CPF/banco/telefone)."""

    model_config = ConfigDict(frozen=True)

    id: str
    nome: str
    municipio: str
    certificacao_organica: bool
    certificacao_vigente: bool
    validade_certificacao: date | None = None


class ItemPedidoValidado(BaseModel):
    """Resultado factual da validação de um item contra catálogo, safra, preço e produtores."""

    model_config = ConfigDict(frozen=True)

    produto_informado: str
    produto_normalizado: str | None = None
    variedade_preco: str | None = None
    encontrado: bool
    quantidade: Decimal | None = None
    unidade: str | None = None
    organico_solicitado: bool = False
    nivel_safra: NivelSafra | None = None
    mes_referencia: str | None = None
    preco_unitario: Decimal | None = None
    desconto_atacado_pct: int = 0
    desconto_aplicado: bool = False
    valor_estimado: Decimal | None = None
    produtores_elegiveis: list[ProdutorElegivel] = Field(default_factory=list)
    capacidade_referencia: Decimal | None = None
    origem_capacidade: str | None = None
    restricoes: list[str] = Field(default_factory=list)
    alertas: list[AlertaTriagem] = Field(default_factory=list)


class PedidoEstruturado(BaseModel):
    """Pedido estruturado factual.

    'tipo' e 'urgencia' permanecem opcionais e abertos até fechamento com David.
    """

    model_config = ConfigDict(frozen=True)

    pedido_id: str | None = None
    comprador: str | None = None
    prazo_informado: str | None = None
    data_entrega_prevista: date | None = None
    data_referencia: date
    tipo: str | None = None
    urgencia: str | None = None
    itens: list[ItemPedidoValidado] = Field(default_factory=list)
    valor_total_estimado: Decimal | None = None
    informacoes_ausentes: list[str] = Field(default_factory=list)
    alertas: list[AlertaTriagem] = Field(default_factory=list)