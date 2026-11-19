"""Schemas de relatórios individuais e dossiê do produtor.

Função:
    Define contratos públicos de saída para produtor_service e relatorio_service.

Não deve:
    - Expor dados pessoais sensíveis (CPF, data de nascimento, chave Pix, dados bancários, telefone)
    - Conter lógica de cálculo

Relações:
    Usa:        pydantic, models.produtor_model, models.produto_model, models.pedido_model
    Usado por:  services.produtor_service, services.relatorio_service, agents.tools
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.pedido_model import PedidoBruto
from models.produto_model import Lote
from models.produtor_model import Produtor, Transacao

StatusCertificacao = Literal["vigente", "vencendo_em_breve", "vencida", "nao_possui"]


class SituacaoCertificacao(BaseModel):
    """Situação da certificação orgânica em relação a uma data de referência."""

    model_config = ConfigDict(frozen=True)

    certificacao_organica: bool
    validade_certificacao: date | None = None
    status: StatusCertificacao
    dias_para_vencer: int | None = None


class ResumoProdutoVendido(BaseModel):
    """Totais vendidos agrupados por produto e unidade real (nunca mistura kg/maço/dúzia)."""

    model_config = ConfigDict(frozen=True)

    produto: str
    unidade: str
    quantidade_total: Decimal
    valor_total: Decimal
    numero_vendas: int


class DossieProdutor(BaseModel):
    """Visão consolidada do produtor sem dados sensíveis."""

    model_config = ConfigDict(frozen=True)

    produtor: Produtor
    certificacao: SituacaoCertificacao
    transacoes: list[Transacao] = Field(default_factory=list)
    lotes: list[Lote] = Field(default_factory=list)
    pedidos_relacionados: list[PedidoBruto] = Field(default_factory=list)


class RelatorioProdutor(BaseModel):
    """Resumo financeiro e operacional calculado em Decimal para um produtor."""

    model_config = ConfigDict(frozen=True)

    produtor_id: str
    produtor_nome: str
    municipio: str
    status_produtor: Literal["ativo", "inativo"]
    data_referencia: date
    data_inicio: date | None = None
    data_fim: date | None = None
    certificacao: SituacaoCertificacao
    total_vendas: Decimal
    total_pago: Decimal
    total_pendente: Decimal
    total_em_atraso: Decimal
    quantidade_transacoes: int
    transacoes_pagas: int
    transacoes_pendentes: int
    transacoes_em_atraso: list[Transacao] = Field(default_factory=list)
    transacoes_a_vencer: list[Transacao] = Field(default_factory=list)
    produtos_vendidos: list[ResumoProdutoVendido] = Field(default_factory=list)
    lotes_entregues: int
    pedidos_relacionados: list[PedidoBruto] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)


class DadosNotificacaoProdutor(BaseModel):
    """Estrutura enxuta para o agente redigir a notificação individual sem calcular valores."""

    model_config = ConfigDict(frozen=True)

    produtor_id: str
    produtor_nome: str
    status_produtor: Literal["ativo", "inativo"]
    data_referencia: date
    total_vendas: Decimal
    total_pendente: Decimal
    total_em_atraso: Decimal
    quantidade_pendencias: int
    certificacao_status: StatusCertificacao
    validade_certificacao: date | None = None
    itens_pendentes: list[Transacao] = Field(default_factory=list)