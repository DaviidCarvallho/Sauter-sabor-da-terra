"""Garante que todos os módulos da estrutura existem e podem ser importados."""

import importlib
import pkgutil

import pytest

PACOTES = ["api", "models", "services", "agents", "rag", "repositories", "storage", "utils"]


def _modulos() -> list[str]:
    nomes = []
    for nome in PACOTES:
        pacote = importlib.import_module(nome)
        nomes.append(nome)
        nomes += [m.name for m in pkgutil.walk_packages(pacote.__path__, prefix=f"{nome}.")]
    return nomes


@pytest.mark.parametrize("modulo", _modulos())
def test_modulo_importa(modulo):
    importlib.import_module(modulo)
