"""Armazenamento no Google Cloud Storage (esqueleto).

Função:
    Implementar o mesmo contrato `Storage` usando um bucket do GCS.

Responsabilidades:
    - Traduzir chaves lógicas (ex.: "contratos/x.pdf") em nomes de objeto: GCS_PREFIX + chave
    - Ler objetos como bytes ou texto e listar por prefixo

Não deve:
    - Ser conhecido por agentes ou serviços (eles usam apenas a interface Storage)
    - Guardar o índice do ChromaDB (o GCS armazena arquivos, não substitui o banco vetorial)

Relações:
    Usa:        google-cloud-storage (extra opcional: pip install -e ".[gcs]"), utils.config
    Usado por:  storage.get_storage(), quando STORAGE_BACKEND=gcs

Status: esqueleto. Será implementado na migração para a nuvem. Enquanto isso,
`get_storage()` recusa STORAGE_BACKEND=gcs com uma mensagem clara.
"""


class GCSStorage:
    def __init__(self, bucket: str, prefix: str = "") -> None:
        raise NotImplementedError("GCSStorage ainda não foi implementado.")

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def read_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        raise NotImplementedError

    def list_keys(self, prefix: str = "") -> list[str]:
        raise NotImplementedError
