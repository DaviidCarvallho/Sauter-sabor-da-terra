"""Schemas de produtos, sazonalidade, preços e lotes.

Função:
    Representa o catálogo de produtos e a rastreabilidade de lotes.

Responsabilidades:
    - Disponibilidade por mês (sazonalidade.csv)
    - Preço convencional e orgânico (tabela_precos_outubro_2026.csv)
    - Lote entregue e sua origem (lotes.csv)

Não deve:
    - Fixar campos antes de conhecer os arquivos

Relações:
    Usa:        pydantic
    Usado por:  repositories.produto_repository, repositories.lote_repository, services.pedido_service, services.documento_service

Observação:
    Arquivo adicionado à estrutura original: sazonalidade, preços e lotes não tinham modelo.

Status: implementado (Fase 3): SazonalidadeProduto, PrecoProduto e Lote.
    Colunas e inconsistências conhecidas: docs/DADOS.md.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Mesma convenção de models/produtor_model.py: aliases = colunas reais dos arquivos;
# campos sensíveis (produtor_cpf) não existem no model e são descartados na leitura.

NivelSafra = Literal["alta", "media", "baixa", "nenhuma"]
UnidadeMedida = Literal["kg", "unidade", "maço", "litro", "dúzia"]


class SazonalidadeProduto(BaseModel):
    """Uma linha de sazonalidade.csv: disponibilidade do produto em cada mês."""

    model_config = ConfigDict(frozen=True)

    produto: str
    jan: NivelSafra
    fev: NivelSafra
    mar: NivelSafra
    abr: NivelSafra
    mai: NivelSafra
    jun: NivelSafra
    jul: NivelSafra
    ago: NivelSafra
    set: NivelSafra
    out: NivelSafra
    nov: NivelSafra
    dez: NivelSafra
    observacao: str = ""


class PrecoProduto(BaseModel):
    """Uma linha de tabela_precos_outubro_2026.csv."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    produto: str
    unidade: UnidadeMedida
    preco_convencional: Decimal | None = Field(default=None, ge=0)
    preco_organico: Decimal | None = Field(default=None, ge=0)
    desconto_atacado_pct: int = Field(ge=0, le=100)
    # O nome da coluna diz "kg", mas o volume usa a unidade do produto (maço, dúzia...).
    volume_minimo_atacado: int = Field(alias="volume_minimo_atacado_kg", ge=0)
    observacao: str = ""

    @field_validator("preco_convencional", "preco_organico", mode="before")
    @classmethod
    def _nd_para_none(cls, valor: object) -> object:
        # 'n/d' (e vazio) significa que o produto não tem esse tipo de preço.
        if isinstance(valor, str) and valor.strip().lower() in {"", "n/d"}:
            return None
        return valor


class Lote(BaseModel):
    """Lote entregue (lotes.csv), sem o CPF do produtor."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    lote_id: str
    data_colheita: date
    data_entrega: date
    produtor_id: str
    produtor_nome: str
    produto: str
    # Mesma ressalva de Transacao: a coluna se chama quantidade_kg, mas a unidade varia.
    quantidade: Decimal = Field(alias="quantidade_kg", gt=0)
    unidade: str | None = None
    comprador: str
    # Formato diferente do id de pedidos.json (PED-2026-SEP-003 x PED-2026-001):
    # é informativo, não serve para ligar o lote a um pedido do JSON.
    pedido_id: str
    # No CSV a coluna mistura número (°C) e o texto "ambiente".
    temperatura_transporte: int | Literal["ambiente"] = Field(alias="temperatura_transporte_c")
    validade: date
    inspecao_visual: str
    observacao: str = ""

    @model_validator(mode="after")
    def _conferir_datas(self) -> "Lote":
        if self.data_entrega < self.data_colheita:
            raise ValueError("data_entrega anterior à data_colheita")
        if self.validade < self.data_entrega:
            raise ValueError("validade anterior à data_entrega")
        return self