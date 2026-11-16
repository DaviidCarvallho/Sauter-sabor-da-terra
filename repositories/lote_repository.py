"""Repositório de lotes.

Função:
    Acesso a lotes.csv (rastreabilidade dos últimos lotes entregues).

Responsabilidades:
    - Buscar lote por identificador e listar lotes por produto ou produtor

Não deve:
    - Aplicar regras de negócio

Relações:
    Usa:        repositories.storage_repository, models.produto_model
    Usado por:  services.documento_service

Observação:
    Arquivo adicionado à estrutura original: lotes.csv não tinha repositório.

Status: implementado (Fase 3).
"""

from models.produto_model import Lote
from repositories.storage_repository import carregar_modelos, ler_csv, normalizar_texto
from storage.base import Storage

ARQUIVO = "lotes.csv"


class LoteRepository:
    """Leitura de lotes.csv. Somente leitura; não aplica regras de negócio."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage

    def listar(self) -> list[Lote]:
        linhas = ler_csv(ARQUIVO, self._storage)
        return carregar_modelos(ARQUIVO, linhas, Lote, campo_id="lote_id")

    def buscar_por_id(self, lote_id: str) -> Lote | None:
        """Busca pelo identificador completo (ex.: 'LOT-2026-0089'), ignorando maiúsculas.

        Identificador que não existe devolve None. Não há busca aproximada: um id
        parecido (como '2024-089') não é o mesmo lote, e adivinhar seria inventar.
        """
        alvo = normalizar_texto(lote_id)
        return next((l for l in self.listar() if normalizar_texto(l.lote_id) == alvo), None)

    def listar_por_produtor(self, produtor_id: str) -> list[Lote]:
        alvo = normalizar_texto(produtor_id)
        return [l for l in self.listar() if normalizar_texto(l.produtor_id) == alvo]

    def listar_por_produto(self, produto: str) -> list[Lote]:
        """Nome exato do produto, sem diferenciar maiúsculas e acentos.

        Sem busca por prefixo ('tomate' não devolve 'tomate cereja'). A tradução entre os
        nomes dos arquivos entra aqui quando o mapa de nomes de produto for decidido.
        """
        alvo = normalizar_texto(produto)
        return [l for l in self.listar() if normalizar_texto(l.produto) == alvo]