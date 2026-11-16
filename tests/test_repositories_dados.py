"""Testes dos repositórios de dados: produtores, financeiro, lotes e pedidos.

Os testes "reais" leem os arquivos de data/ e conferem os fatos documentados em
docs/DADOS.md. Os testes de erro usam uma cópia temporária dos dados, alterada de propósito.
"""

import shutil
from datetime import date
from pathlib import Path

import pytest

from repositories.financeiro_repository import FinanceiroRepository
from repositories.lote_repository import LoteRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produtor_repository import ProdutorRepository
from repositories.storage_repository import DadoInvalidoError
from storage.local_storage import LocalStorage

DADOS = Path(__file__).resolve().parent.parent / "data"
ARQUIVOS = ["produtores.csv", "financeiro.csv", "lotes.csv", "pedidos.json"]

pytestmark = pytest.mark.skipif(
    not all((DADOS / a).exists() for a in ARQUIVOS), reason="data/ sem os arquivos reais"
)

SENSIVEIS = ["831.452.674-90", "723.016.498-55", "maria.graca@email.com", "1975-03-12"]


@pytest.fixture
def storage():
    return LocalStorage(DADOS)


@pytest.fixture
def storage_copia(tmp_path):
    """Cópia editável dos dados reais."""
    for nome in ARQUIVOS:
        shutil.copy(DADOS / nome, tmp_path / nome)
    return LocalStorage(tmp_path), tmp_path


def _editar(tmp_path, arquivo, antigo, novo):
    caminho = tmp_path / arquivo
    texto = caminho.read_text(encoding="utf-8")
    assert antigo in texto
    caminho.write_text(texto.replace(antigo, novo, 1), encoding="utf-8")


# ---------- ProdutorRepository ----------

def test_lista_os_18_produtores_e_filtra_ativos(storage):
    repo = ProdutorRepository(storage)
    assert len(repo.listar()) == 18
    ativos = repo.listar(apenas_ativos=True)
    assert len(ativos) == 17 and "P015" not in {p.id for p in ativos}


def test_busca_produtor_por_id_ignorando_caixa_e_espacos(storage):
    repo = ProdutorRepository(storage)
    assert repo.buscar_por_id(" p001 ").nome == "Maria das Graças Silva Ferreira"
    assert repo.buscar_por_id("P999") is None


def test_filtra_por_produto_sem_diferenciar_acento_nem_buscar_prefixo(storage):
    repo = ProdutorRepository(storage)
    assert "P001" in {p.id for p in repo.listar_por_produto("GOIABA")}
    assert {p.id for p in repo.listar_por_produto("tomate cereja")} == {"P004"}
    assert all("tomate" in p.produtos for p in repo.listar_por_produto("tomate"))  # nome exato, sem prefixo
    assert repo.listar_por_produto("unobtanium") == []
    # 'pimentao' sem acento encontra 'pimentão' do cadastro
    assert repo.listar_por_produto("pimentao") == repo.listar_por_produto("pimentão") != []


def test_filtra_por_certificacao_organica(storage):
    repo = ProdutorRepository(storage)
    assert len(repo.listar_por_certificacao(True)) == 9
    assert len(repo.listar_por_certificacao(False)) == 9


def test_certificacoes_do_dataset_p008_vencida_e_p004_proxima_do_fim(storage):
    # O repositório só entrega o dado; quem compara com a data de referência é o serviço.
    repo = ProdutorRepository(storage)
    assert repo.buscar_por_id("P008").validade_certificacao == date(2026, 9, 30)
    assert repo.buscar_por_id("P004").validade_certificacao == date(2026, 12, 1)


def test_identifica_produtor_pelo_telefone_sem_expor_o_telefone(storage):
    repo = ProdutorRepository(storage)
    for formato in ["(87) 99812-3456", "87998123456", "87 99812 3456"]:
        assert repo.buscar_por_telefone(formato).id == "P001"
    assert repo.buscar_por_telefone("(87) 90000-0000") is None
    assert repo.buscar_por_telefone("123") is None  # curto demais para identificar alguém
    assert "telefone" not in repo.buscar_por_id("P001").model_dump()


def test_produtores_nao_expoem_dados_sensiveis(storage):
    saida = "".join(p.model_dump_json() for p in ProdutorRepository(storage).listar())
    assert not any(valor in saida for valor in SENSIVEIS)


def test_produtores_com_id_duplicado_geram_erro(storage_copia):
    storage, tmp = storage_copia
    _editar(tmp, "produtores.csv", "P002,", "P001,")
    with pytest.raises(DadoInvalidoError, match="duplicado: P001"):
        ProdutorRepository(storage).listar()


def test_produtor_com_valor_invalido_informa_arquivo_e_linha(storage_copia):
    storage, tmp = storage_copia
    _editar(tmp, "produtores.csv", ",sim,2027-06-15,", ",talvez,2027-06-15,")
    with pytest.raises(DadoInvalidoError) as erro:
        ProdutorRepository(storage).listar()
    assert "produtores.csv" in str(erro.value) and "linha 2" in str(erro.value)
    assert "831.452.674-90" not in str(erro.value)


def test_arquivo_ausente_levanta_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        ProdutorRepository(LocalStorage(tmp_path)).listar()


# ---------- FinanceiroRepository ----------

def test_lista_as_30_transacoes_sem_dados_sensiveis(storage):
    transacoes = FinanceiroRepository(storage).listar()
    assert len(transacoes) == 30
    assert sum(t.valor_total for t in transacoes) == 24634
    saida = "".join(t.model_dump_json() for t in transacoes)
    assert not any(valor in saida for valor in SENSIVEIS)


def test_transacoes_por_produtor_e_periodo(storage):
    repo = FinanceiroRepository(storage)
    todas = repo.listar_por_produtor("p001")
    assert todas and all(t.produtor_id == "P001" for t in todas)
    setembro = repo.listar_por_produtor("P001", data_inicio=date(2026, 9, 1), data_fim=date(2026, 9, 30))
    assert setembro and all(date(2026, 9, 1) <= t.data <= date(2026, 9, 30) for t in setembro)
    # limites inclusivos: uma janela de um único dia traz as vendas desse dia
    dia = todas[0].data
    assert todas[0] in repo.listar_por_produtor("P001", data_inicio=dia, data_fim=dia)
    assert repo.listar_por_produtor("P001", data_inicio=date(2030, 1, 1)) == []


def test_produtor_sem_transacoes_ou_inexistente_devolve_lista_vazia(storage):
    repo = FinanceiroRepository(storage)
    assert repo.listar_por_produtor("P015") == []  # produtor inativo, sem vendas
    assert repo.listar_por_produtor("P999") == []


def test_pendencias_e_vencimentos_conforme_data_de_referencia(storage):
    repo = FinanceiroRepository(storage)
    assert len(repo.listar_pendentes()) == 10
    vencidas_30_10 = repo.listar_pendentes(vencidas_antes_de=date(2026, 10, 30))
    assert {t.id_transacao for t in vencidas_30_10} == {
        "FIN-2026-005", "FIN-2026-006", "FIN-2026-007", "FIN-2026-013", "FIN-2026-014",
    }
    assert sum(t.valor_total for t in vencidas_30_10) == 8690
    vencidas_14_11 = repo.listar_pendentes(vencidas_antes_de=date(2026, 11, 14))
    assert len(vencidas_14_11) == 8 and sum(t.valor_total for t in vencidas_14_11) == 10500
    # vence exatamente na data de referência: ainda não está vencida
    assert repo.listar_pendentes(vencidas_antes_de=date(2026, 10, 23)) != repo.listar_pendentes(
        vencidas_antes_de=date(2026, 10, 24)
    )


def test_pendencias_de_um_produtor(storage):
    repo = FinanceiroRepository(storage)
    do_produtor = repo.listar_pendentes(produtor_id="P004")
    assert do_produtor and all(t.produtor_id == "P004" and t.status_pagamento == "pendente" for t in do_produtor)


def test_busca_transacao_por_id(storage):
    repo = FinanceiroRepository(storage)
    assert repo.buscar_por_id("fin-2026-001").produto == "goiaba paluma"
    assert repo.buscar_por_id("FIN-2026-999") is None


def test_transacao_inconsistente_interrompe_a_leitura(storage_copia):
    storage, tmp = storage_copia
    _editar(tmp, "financeiro.csv", ",120,4.50,540.00,", ",120,4.50,541.00,")
    with pytest.raises(DadoInvalidoError, match="financeiro.csv, linha 2"):
        FinanceiroRepository(storage).listar()


# ---------- LoteRepository ----------

def test_lista_os_20_lotes_sem_cpf(storage):
    lotes = LoteRepository(storage).listar()
    assert len(lotes) == 20
    assert not any("723.016.498-55" in l.model_dump_json() for l in lotes)
    assert {l.temperatura_transporte for l in lotes} >= {"ambiente", 8}


def test_busca_lote_por_id_e_nao_adivinha_id_inexistente(storage):
    repo = LoteRepository(storage)
    assert repo.buscar_por_id("lot-2026-0104").produtor_id == "P008"
    assert repo.buscar_por_id("2024-089") is None  # o exemplo do enunciado não existe nos dados
    assert repo.buscar_por_id("LOT-2026-0001") is None
    assert repo.buscar_por_id("0104") is None  # id parcial não vale
    assert repo.buscar_por_id("LOT-2026-010") is None


def test_lotes_por_produtor_e_por_produto(storage):
    repo = LoteRepository(storage)
    assert all(l.produtor_id == "P003" for l in repo.listar_por_produtor("p003"))
    assert repo.listar_por_produtor("P015") == []
    assert repo.listar_por_produto("Queijo Coalho")
    assert repo.listar_por_produto("tomate")
    assert all(l.produto == "tomate" for l in repo.listar_por_produto("tomate"))  # sem prefixo
    assert repo.listar_por_produto("unobtanium") == []


def test_busca_de_lote_por_produto_nao_usa_prefixo(storage_copia):
    storage, tmp = storage_copia
    antes = len(LoteRepository(storage).listar_por_produto("tomate"))
    _editar(tmp, "lotes.csv", ",tomate,", ",tomate cereja,")  # um lote vira 'tomate cereja'
    repo = LoteRepository(storage)
    assert len(repo.listar_por_produto("tomate")) == antes - 1
    assert len(repo.listar_por_produto("tomate cereja")) == 1


def test_lote_entregue_apos_certificacao_vencer_esta_nos_dados(storage):
    # Caso do DADOS.md: lote do P008 entregue em 01/10, com a certificação vencida em 30/09.
    lote = LoteRepository(storage).buscar_por_id("LOT-2026-0104")
    produtor = ProdutorRepository(storage).buscar_por_id(lote.produtor_id)
    assert lote.data_entrega == date(2026, 10, 1)
    assert produtor.validade_certificacao < lote.data_entrega


# ---------- PedidoRepository ----------

def test_lista_os_15_pedidos_e_busca_por_id(storage):
    repo = PedidoRepository(storage)
    pedidos = repo.listar()
    assert len(pedidos) == 15
    assert all(p.status == "pendente" for p in pedidos)
    assert repo.buscar_por_id("ped-2026-006").data_recebimento.date() == date(2026, 10, 29)
    assert repo.buscar_por_id("PED-2026-099") is None


def test_pedidos_de_um_remetente_por_telefone_ou_email(storage):
    repo = PedidoRepository(storage)
    # PED-012 (P001) e PED-015 (P003) vêm do telefone do próprio produtor
    assert [p.id for p in repo.listar_por_remetente("87998123456")] == ["PED-2026-012"]
    assert [p.id for p in repo.listar_por_remetente("(87) 99745-1098")] == ["PED-2026-015"]
    primeiro_email = next(p for p in repo.listar() if "@" in p.remetente)
    assert primeiro_email in repo.listar_por_remetente(primeiro_email.remetente.upper())
    assert repo.listar_por_remetente("ninguem@exemplo.com") == []


def test_telefone_do_pedido_identifica_o_produtor(storage):
    pedido = PedidoRepository(storage).buscar_por_id("PED-2026-012")
    produtor = ProdutorRepository(storage).buscar_por_telefone(pedido.remetente)
    assert produtor.id == "P001"


def test_json_malformado_ou_canal_invalido_informam_o_registro(storage_copia):
    storage, tmp = storage_copia
    _editar(tmp, "pedidos.json", '"canal": "whatsapp"', '"canal": "telegrama"')
    with pytest.raises(DadoInvalidoError, match="pedidos.json, registro"):
        PedidoRepository(storage).listar()
    (tmp / "pedidos.json").write_text('[{"id": }]', encoding="utf-8")
    with pytest.raises(DadoInvalidoError, match="JSON inválido"):
        PedidoRepository(storage).listar()


def test_pedido_repository_e_somente_leitura(storage):
    publicos = {n for n in dir(PedidoRepository) if not n.startswith("_")}
    assert publicos == {"listar", "buscar_por_id", "listar_por_remetente"}