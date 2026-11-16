"""Repositório de pedidos.

Função:
    Acesso a pedidos.json (somente leitura na primeira versão).

Responsabilidades:
    - Listar pedidos e buscar por identificador ou produtor

Não deve:
    - Gravar no JSON (decisão pendente sobre persistir pedidos processados)

Relações:
    Usa:        repositories.storage_repository, models.pedido_model
    Usado por:  services.pedido_service, services.produtor_service

Status: implementado (Fase 3).
"""

from models.pedido_model import PedidoBruto
from repositories.storage_repository import (
    carregar_modelos,
    ler_json,
    normalizar_texto,
    somente_digitos,
)
from storage.base import Storage

ARQUIVO = "pedidos.json"


class PedidoRepository:
    """Leitura de pedidos.json. Somente leitura: não grava nada no arquivo."""

    def __init__(self, storage: Storage | None = None) -> None:
        self._storage = storage

    def listar(self) -> list[PedidoBruto]:
        registros = ler_json(ARQUIVO, self._storage)
        return carregar_modelos(
            ARQUIVO, registros, PedidoBruto, campo_id="id", rotulo="registro", inicio=1
        )

    def buscar_por_id(self, pedido_id: str) -> PedidoBruto | None:
        alvo = normalizar_texto(pedido_id)
        return next((p for p in self.listar() if normalizar_texto(p.id) == alvo), None)

    def listar_por_remetente(self, remetente: str) -> list[PedidoBruto]:
        """Pedidos enviados por um remetente (e-mail, telefone ou nome da empresa).

        Telefones são comparados só pelos dígitos, ignorando a formatação. O arquivo não
        tem campo de produtor: pedidos de um produtor só podem ser identificados pelo
        telefone do remetente (ver docs/DADOS.md, seção 8).
        """
        digitos = somente_digitos(remetente)
        alvo = normalizar_texto(remetente)

        def confere(pedido: PedidoBruto) -> bool:
            if len(digitos) >= 8 and somente_digitos(pedido.remetente) == digitos:
                return True
            return normalizar_texto(pedido.remetente) == alvo

        return [p for p in self.listar() if confere(p)]