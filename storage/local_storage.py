"""Armazenamento em disco local, a partir de uma pasta raiz."""

from pathlib import Path

# Arquivos de controle que não são dados da cooperativa.
_IGNORED_NAMES = {".gitkeep", ".DS_Store"}


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, key: str) -> Path:
        """Converte a chave em caminho, bloqueando saídas da pasta raiz (ex.: '../.env')."""
        path = (self._root / key).resolve()
        if path != self._root and self._root not in path.parents:
            raise ValueError(f"Chave fora da raiz de dados: {key!r}")
        return path

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(key).decode(encoding)

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self._resolve(prefix) if prefix else self._root
        if not base.is_dir():
            return []
        return sorted(
            p.relative_to(self._root).as_posix()
            for p in base.rglob("*")
            if p.is_file() and p.name not in _IGNORED_NAMES
        )
