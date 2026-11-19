"""Testes dos serviços de produtores e relatórios (dados reais, sem LLM)."""

from datetime import date
from decimal import Decimal

import pytest

from services.produtor_service import ProdutorService
from services.relatorio_service import RelatorioService
from storage.local_storage import LocalStorage


@pytest.fixture
def servicos():
    from pathlib import Path
    from repositories.financeiro_repository import FinanceiroRepository
    from repositories.lote_repository import LoteRepository
    from repositories.pedido_repository import PedidoRepository
    from repositories.produto_repository import ProdutoRepository
    from repositories.produtor_repository import ProdutorRepository

    storage = LocalStorage(Path(__file__).resolve().parent.parent / "data")
    prod_svc = ProdutorService(
        produtor_repo=ProdutorRepository(storage),
        pedido_repo=PedidoRepository(storage),
        financeiro_repo=FinanceiroRepository(storage),
        lote_repo=LoteRepository(storage),
        produto_repo=ProdutoRepository(storage),
    )
    rel_svc = RelatorioService(produtor_service=prod_svc)
    return prod_svc, rel_svc


def test_p001_reune_pedido_por_telefone_sem_expor_dado_pessoal(servicos):
    prod_svc, _ = servicos
    dossie = prod_svc.obter_dossie("P001", data_referencia=date(2026, 10, 30))

    assert dossie.produtor.id == "P001"
    assert any(p.id == "PED-2026-012" for p in dossie.pedidos_relacionados)
    assert not hasattr(dossie.produtor, "telefone")
    assert not hasattr(dossie.produtor, "cpf")
    assert dossie.certificacao.status == "vigente"


def test_p004_certificacao_vencendo_em_ate_60_dias(servicos):
    prod_svc, rel_svc = servicos
    rel = rel_svc.gerar_relatorio_produtor("P004", data_referencia=date(2026, 10, 30))

    assert rel.certificacao.status == "vencendo_em_breve"
    assert any("vence em breve" in a.lower() for a in rel.alertas)
    assert rel.total_pendente == Decimal("1020.00")
    assert rel.total_em_atraso == Decimal("1020.00")
    unidades = {p.produto: p.unidade for p in rel.produtos_vendidos}
    assert unidades["alface"] == "unidade"
    assert unidades["coentro"] == "maço"


def test_p008_certificacao_vencida_gera_alerta(servicos):
    _, rel_svc = servicos
    rel = rel_svc.gerar_relatorio_produtor("P008", data_referencia=date(2026, 10, 30))

    assert rel.certificacao.status == "vencida"
    assert any("vencida" in a.lower() for a in rel.alertas)


def test_p015_inativo_sem_transacoes_nao_falha(servicos):
    _, rel_svc = servicos
    rel = rel_svc.gerar_relatorio_produtor("P015", data_referencia=date(2026, 10, 30))

    assert rel.status_produtor == "inativo"
    assert rel.total_vendas == Decimal("0.00")
    assert rel.total_pendente == Decimal("0.00")
    assert rel.quantidade_transacoes == 0
    assert any("inativo" in a.lower() for a in rel.alertas)


def test_atraso_depende_da_data_de_referencia(servicos):
    _, rel_svc = servicos
    rel_out = rel_svc.gerar_relatorio_produtor("P016", data_referencia=date(2026, 10, 30))
    rel_nov = rel_svc.gerar_relatorio_produtor("P016", data_referencia=date(2026, 11, 14))

    assert rel_out.total_pendente == Decimal("1200.00")
    assert rel_out.total_em_atraso == Decimal("0.00")
    assert rel_nov.total_em_atraso == Decimal("1200.00")


def test_preparar_dados_notificacao(servicos):
    _, rel_svc = servicos
    notif = rel_svc.preparar_dados_notificacao("P003", data_referencia=date(2026, 10, 30))

    assert notif.produtor_id == "P003"
    assert notif.total_em_atraso == Decimal("6020.00")
    assert notif.quantidade_pendencias == 2