"""Repositório de produtores.

Função:
    Acesso a produtores.csv.

Responsabilidades:
    - Listar e buscar produtores; filtrar por produto ou certificação

Não deve:
    - Aplicar regras de negócio

Relações:
    Usa:        repositories.storage_repository, models.produtor_model
    Usado por:  services.pedido_service, services.produtor_service

Status: implementado (Fase 3).
"""

from models.produtor_model import Produtor
from repositories.storage_repository import (
    carregar_modelos,
    ler_csv,
    normalizar_texto,
    somente_digitos,
)
from storage.base import Storage

ARQUIVO = "produtores.csv"


class ProdutorRepository:
    """Leitura de produtores.csv. Somente leitura; não aplica regras de negócio."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage

    def _carregar(self) -> tuple[list[dict[str, str]], list[Produtor]]:
        linhas = ler_csv(ARQUIVO, self._storage)
        return linhas, carregar_modelos(ARQUIVO, linhas, Produtor, campo_id="id")

    def listar(self, *, apenas_ativos: bool = False) -> list[Produtor]:
        produtores = self._carregar()[1]
        return [p for p in produtores if not apenas_ativos or p.status == "ativo"]

    def buscar_por_id(self, produtor_id: str) -> Produtor | None:
        """Ignora maiúsculas e espaços ('p001' encontra 'P001'). Devolve None se não existir."""
        alvo = normalizar_texto(produtor_id)
        return next((p for p in self.listar() if normalizar_texto(p.id) == alvo), None)

    def listar_por_produto(self, produto: str, *, apenas_ativos: bool = False) -> list[Produtor]:
        """Produtores que listam o produto no cadastro (nome exato, sem diferenciar acento).

        Os nomes do cadastro diferem dos de sazonalidade e preços (ver docs/DADOS.md, seção 7).
        A tradução entre eles será feita quando o mapa de nomes de produto for decidido.
        """
        alvo = normalizar_texto(produto)
        return [
            p
            for p in self.listar(apenas_ativos=apenas_ativos)
            if alvo in {normalizar_texto(item) for item in p.produtos}
        ]

    def listar_por_certificacao(
        self, organica: bool = True, *, apenas_ativos: bool = False
    ) -> list[Produtor]:
        """Filtra pelo cadastro ('sim'/'nao'). Não verifica se a certificação está vigente:
        isso depende de uma data de referência e fica no serviço."""
        return [
            p
            for p in self.listar(apenas_ativos=apenas_ativos)
            if p.certificacao_organica == organica
        ]

    def buscar_por_telefone(self, telefone: str) -> Produtor | None:
        """Identifica o produtor pelo telefone (ex.: remetente de um pedido do WhatsApp).

        O telefone não faz parte do model devolvido; é usado só para a comparação, que
        ignora a formatação. Devolve None se não houver correspondência.
        """
        digitos = somente_digitos(telefone)
        if len(digitos) < 8:
            return None
        linhas, produtores = self._carregar()
        for linha, produtor in zip(linhas, produtores):
            if somente_digitos(linha.get("telefone", "")) == digitos:
                return produtor
        return None