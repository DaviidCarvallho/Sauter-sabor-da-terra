"""Repositório financeiro.

Função:
    Acesso a financeiro.csv (transações de set-out/2026).

Responsabilidades:
    - Buscar transações por produtor e período; identificar pendências

Não deve:
    - Calcular relatórios (função do relatorio_service)

Relações:
    Usa:        repositories.storage_repository, models.produtor_model
    Usado por:  services.produtor_service

Status: implementado (Fase 3).
"""

from datetime import date

from models.produtor_model import Transacao
from repositories.storage_repository import (
    carregar_modelos,
    ler_csv,
    normalizar_texto,
)
from storage.base import Storage

ARQUIVO = "financeiro.csv"


class FinanceiroRepository:
    """Leitura de financeiro.csv. Somente leitura; os relatórios são calculados no serviço."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage

    def listar(self) -> list[Transacao]:
        linhas = ler_csv(ARQUIVO, self._storage)
        return carregar_modelos(ARQUIVO, linhas, Transacao, campo_id="id_transacao")

    def buscar_por_id(self, id_transacao: str) -> Transacao | None:
        alvo = normalizar_texto(id_transacao)
        return next((t for t in self.listar() if normalizar_texto(t.id_transacao) == alvo), None)

    def listar_por_produtor(
        self,
        produtor_id: str,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> list[Transacao]:
        """Transações do produtor, filtradas pela data da venda (limites inclusivos).

        Produtor sem transações (ou que não existe) devolve lista vazia.
        """
        alvo = normalizar_texto(produtor_id)
        return [
            t
            for t in self.listar()
            if normalizar_texto(t.produtor_id) == alvo
            and (data_inicio is None or t.data >= data_inicio)
            and (data_fim is None or t.data <= data_fim)
        ]

    def listar_pendentes(
        self,
        *,
        produtor_id: str | None = None,
        vencidas_antes_de: date | None = None,
    ) -> list[Transacao]:
        """Transações com status 'pendente'.

        Com 'vencidas_antes_de', devolve só as que venceram antes dessa data
        (data_vencimento < data). Quem escolhe a data de referência (hoje, por padrão)
        é o serviço; o repositório não decide o que é "atraso".
        """
        alvo = normalizar_texto(produtor_id) if produtor_id is not None else None
        return [
            t
            for t in self.listar()
            if t.status_pagamento == "pendente"
            and (alvo is None or normalizar_texto(t.produtor_id) == alvo)
            and (vencidas_antes_de is None or t.data_vencimento < vencidas_antes_de)
        ]