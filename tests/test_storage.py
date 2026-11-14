import pytest

from storage.local_storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    (tmp_path / "contratos").mkdir()
    (tmp_path / "contratos" / "a.txt").write_text("olá", encoding="utf-8")
    (tmp_path / "contratos" / ".gitkeep").touch()
    (tmp_path / "produtores.csv").write_bytes(b"id\n1\n")
    return LocalStorage(tmp_path)


def test_le_texto_e_bytes(storage):
    assert storage.read_text("contratos/a.txt") == "olá"
    assert storage.read_bytes("produtores.csv") == b"id\n1\n"


def test_exists(storage):
    assert storage.exists("contratos/a.txt")
    assert not storage.exists("contratos/inexistente.txt")
    assert not storage.exists("contratos")  # pasta não é arquivo


def test_arquivo_inexistente_levanta_erro(storage):
    with pytest.raises(FileNotFoundError):
        storage.read_text("nao_existe.txt")


def test_list_keys_com_e_sem_prefixo_ignora_gitkeep(storage):
    assert storage.list_keys() == ["contratos/a.txt", "produtores.csv"]
    assert storage.list_keys("contratos") == ["contratos/a.txt"]
    assert storage.list_keys("pasta_inexistente") == []


def test_bloqueia_path_traversal(storage):
    with pytest.raises(ValueError):
        storage.read_text("../segredo.txt")
