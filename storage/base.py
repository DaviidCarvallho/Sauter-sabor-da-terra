"""Contrato de armazenamento de arquivos.

Agentes, serviços e repositórios dependem desta interface, nunca de caminhos
físicos. Os arquivos são identificados por *chaves lógicas* relativas à raiz
dos dados, sempre com "/" (ex.: "contratos/mercado_bom_preco.pdf").
Trocar o armazenamento local pelo Google Cloud Storage significa apenas
fornecer outra implementação desta interface.
"""

from typing import Protocol


class Storage(Protocol):
    def exists(self, key: str) -> bool:
        """Indica se existe um arquivo com essa chave."""

    def read_bytes(self, key: str) -> bytes:
        """Lê o arquivo como bytes (PDF, DOCX). Lança FileNotFoundError se não existir."""

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        """Lê o arquivo como texto (CSV, JSON). Lança FileNotFoundError se não existir."""

    def list_keys(self, prefix: str = "") -> list[str]:
        """Lista as chaves de arquivos sob o prefixo, em ordem alfabética."""
