"""Testes do parsing compartilhado de CSV e JSON (repositories/storage_repository.py)."""

import pytest

from models.produtor_model import Produtor
from repositories.storage_repository import (
    DadoInvalidoError,
    carregar_modelos,
    ler_csv,
    ler_json,
    normalizar_texto,
    somente_digitos,
)
from storage.local_storage import LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path)


def _escrever(tmp_path, nome, conteudo, encoding="utf-8"):
    (tmp_path / nome).write_bytes(conteudo.encode(encoding))


def test_le_csv_com_aspas_espacos_e_celula_vazia(tmp_path, storage):
    _escrever(tmp_path, "a.csv", 'id, nome ,obs\nP1, Ana ,"Sítio, Zona Rural"\nP2,Bia,\n')
    assert ler_csv("a.csv", storage) == [
        {"id": "P1", "nome": "Ana", "obs": "Sítio, Zona Rural"},
        {"id": "P2", "nome": "Bia", "obs": ""},
    ]


def test_aceita_bom_do_excel_e_ignora_linhas_em_branco(tmp_path, storage):
    _escrever(tmp_path, "a.csv", "\ufeffid,nome\n\nP1,Ana\n\n")
    assert ler_csv("a.csv", storage) == [{"id": "P1", "nome": "Ana"}]


def test_delimitador_configuravel(tmp_path, storage):
    _escrever(tmp_path, "a.csv", "id;nome\nP1;Ana\n")
    assert ler_csv("a.csv", storage, delimitador=";") == [{"id": "P1", "nome": "Ana"}]


def test_linha_com_colunas_a_mais_ou_a_menos_informa_a_linha(tmp_path, storage):
    _escrever(tmp_path, "a.csv", "id,nome\nP1,Ana\nP2\n")
    with pytest.raises(DadoInvalidoError) as erro:
        ler_csv("a.csv", storage)
    assert "linha 3" in str(erro.value)
    assert erro.value.arquivo == "a.csv"


def test_arquivo_vazio_e_cabecalho_invalido(tmp_path, storage):
    _escrever(tmp_path, "vazio.csv", "")
    _escrever(tmp_path, "cab.csv", "id,,nome\n1,2,3\n")
    with pytest.raises(DadoInvalidoError, match="vazio"):
        ler_csv("vazio.csv", storage)
    with pytest.raises(DadoInvalidoError, match="cabeçalho"):
        ler_csv("cab.csv", storage)


def test_arquivo_inexistente_levanta_file_not_found(storage):
    with pytest.raises(FileNotFoundError):
        ler_csv("nao_existe.csv", storage)
    with pytest.raises(FileNotFoundError):
        ler_json("nao_existe.json", storage)


def test_le_json_e_informa_linha_do_erro(tmp_path, storage):
    _escrever(tmp_path, "ok.json", '[{"id": 1}]')
    _escrever(tmp_path, "ruim.json", '[\n  {"id": 1},\n  {"id": }\n]')
    assert ler_json("ok.json", storage) == [{"id": 1}]
    with pytest.raises(DadoInvalidoError) as erro:
        ler_json("ruim.json", storage)
    assert "linha 3" in str(erro.value)


LINHA_PRODUTOR = {
    "id": "P1",
    "nome_completo": "Ana",
    "cpf": "111.222.333-44",
    "municipio": "Garanhuns",
    "produtos": "goiaba, manga",
    "certificacao_organica": "nao",
    "validade_certificacao": "",
    "status": "ativo",
}


def test_carregar_modelos_converte_e_descarta_campos_sensiveis():
    [produtor] = carregar_modelos("p.csv", [LINHA_PRODUTOR], Produtor, campo_id="id")
    assert produtor.nome == "Ana"
    assert produtor.produtos == ["goiaba", "manga"]
    assert "cpf" not in produtor.model_dump()


def test_erro_de_validacao_informa_arquivo_linha_e_campo_sem_vazar_valores():
    ruim = {**LINHA_PRODUTOR, "status": "suspenso"}
    with pytest.raises(DadoInvalidoError) as erro:
        carregar_modelos("p.csv", [LINHA_PRODUTOR, ruim], Produtor)
    texto = str(erro.value)
    assert "p.csv" in texto and "linha 3" in texto and "status" in texto
    assert "111.222.333-44" not in texto  # CPF não entra na mensagem


def test_posicao_de_registros_json_comeca_em_1():
    ruim = {**LINHA_PRODUTOR, "status": "suspenso"}
    with pytest.raises(DadoInvalidoError, match="registro 1"):
        carregar_modelos("p.json", [ruim], Produtor, rotulo="registro", inicio=1)


def test_id_duplicado_gera_erro():
    with pytest.raises(DadoInvalidoError, match="duplicado: P1"):
        carregar_modelos("p.csv", [LINHA_PRODUTOR, LINHA_PRODUTOR], Produtor, campo_id="id")


def test_exige_lista_de_objetos():
    with pytest.raises(DadoInvalidoError):
        carregar_modelos("p.json", {"id": 1}, Produtor)  # type: ignore[arg-type]


def test_normalizar_texto_e_somente_digitos():
    assert normalizar_texto("  Pimentão   VERDE ") == "pimentao verde"
    assert normalizar_texto("PED-2026-001") == "ped-2026-001"
    assert somente_digitos("(87) 99812-3456") == "87998123456"