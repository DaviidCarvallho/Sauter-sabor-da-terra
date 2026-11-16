"""Schemas de produtores e financeiro.

Função:
    Representa o cadastro dos produtores e suas transações financeiras.

Responsabilidades:
    - Produtor: identificação, município, produtos e certificações
    - Transação financeira: vendas e pagamentos (set-out/2026)

Não deve:
    - Fixar campos antes de conhecer produtores.csv e financeiro.csv

Relações:
    Usa:        pydantic
    Usado por:  repositories.produtor_repository, repositories.financeiro_repository, services.produtor_service

Observação:
    Os campos seguem as colunas reais dos arquivos. CPF, dados bancários, e-mail e data de nascimento
    não fazem parte do model (decisão 8 do PR de dados: mínimo de informações sensíveis).

Status: implementado (Fase 3): Produtor e Transacao, a partir de produtores.csv e financeiro.csv.
    Colunas e inconsistências conhecidas: docs/DADOS.md.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Convenção dos models de dados da cooperativa:
# - Os aliases são os nomes das colunas reais dos arquivos; o repositório faz
#   Modelo.model_validate(linha) e os campos que não existem no model (cpf,
#   dados bancários etc.) são descartados na leitura (decisão 8: mínimo de dados sensíveis).
# - Valores vazios de campos opcionais viram None.


def _vazio_para_none(valor: object) -> object:
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


class Produtor(BaseModel):
    """Produtor cadastrado, sem dados pessoais ou bancários."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: str
    nome: str = Field(alias="nome_completo")
    municipio: str
    produtos: list[str]
    certificacao_organica: bool
    validade_certificacao: date | None = None
    status: Literal["ativo", "inativo"]

    @field_validator("produtos", mode="before")
    @classmethod
    def _separar_produtos(cls, valor: object) -> object:
        # No CSV, os produtos são uma lista separada por vírgula dentro de uma célula.
        if isinstance(valor, str):
            return [item.strip() for item in valor.split(",") if item.strip()]
        return valor

    @field_validator("certificacao_organica", mode="before")
    @classmethod
    def _sim_nao_para_bool(cls, valor: object) -> object:
        if isinstance(valor, str):
            texto = valor.strip().lower()
            if texto == "sim":
                return True
            if texto in {"nao", "não"}:
                return False
            raise ValueError("esperado 'sim' ou 'nao'")
        return valor

    @field_validator("validade_certificacao", mode="before")
    @classmethod
    def _validade_vazia(cls, valor: object) -> object:
        return _vazio_para_none(valor)


class Transacao(BaseModel):
    """Venda registrada no financeiro, sem CPF do produtor nem chave Pix."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id_transacao: str
    data: date
    produtor_id: str
    produtor_nome: str
    comprador: str
    tipo: str
    produto: str
    # A coluna do CSV se chama quantidade_kg, mas a unidade real varia por produto
    # (kg, maço, unidade, dúzia). 'unidade' é preenchida por quem conhece a tabela de preços.
    quantidade: Decimal = Field(alias="quantidade_kg", gt=0)
    unidade: str | None = None
    valor_unitario: Decimal = Field(ge=0)
    valor_total: Decimal = Field(ge=0)
    forma_pagamento: str
    status_pagamento: Literal["pago", "pendente"]
    data_vencimento: date
    data_pagamento: date | None = None
    observacao: str = ""

    @field_validator("data_pagamento", mode="before")
    @classmethod
    def _pagamento_vazio(cls, valor: object) -> object:
        return _vazio_para_none(valor)

    @model_validator(mode="after")
    def _conferir_consistencia(self) -> "Transacao":
        # Integridade do dado (não é regra de negócio): totais e status precisam fechar.
        esperado = self.quantidade * self.valor_unitario
        if abs(esperado - self.valor_total) > Decimal("0.01"):
            raise ValueError(
                f"valor_total ({self.valor_total}) difere de quantidade x valor_unitario ({esperado})"
            )
        if self.status_pagamento == "pago" and self.data_pagamento is None:
            raise ValueError("transação paga sem data_pagamento")
        if self.status_pagamento == "pendente" and self.data_pagamento is not None:
            raise ValueError("transação pendente com data_pagamento preenchida")
        return self