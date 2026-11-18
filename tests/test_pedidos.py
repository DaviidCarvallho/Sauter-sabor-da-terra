"""Testes das validações determinísticas de pedidos (sem LLM)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from models.pedido_model import ItemPedidoEntrada
from repositories.lote_repository import LoteRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produto_repository import ProdutoRepository
from repositories.produtor_repository import ProdutorRepository
from services.pedido_service import PedidoService
from services.produtor_service import ProdutorService
from storage.local_storage import LocalStorage


@pytest.fixture
def pedido_service():
    storage = LocalStorage(Path(__file__).resolve().parent.parent / "data")
    produtor_repo = ProdutorRepository(storage)
    pedido_repo = PedidoRepository(storage)
    produto_repo = ProdutoRepository(storage)
    lote_repo = LoteRepository(storage)
    produtor_svc = ProdutorService(
        produtor_repo=produtor_repo,
        pedido_repo=pedido_repo,
        lote_repo=lote_repo,
        produto_repo=produto_repo,
    )
    return PedidoService(
        pedido_repo=pedido_repo,
        produtor_repo=produtor_repo,
        produto_repo=produto_repo,
        lote_repo=lote_repo,
        produtor_service=produtor_svc,
    )


def test_normalizacao_nao_confunde_tomate_e_tomate_cereja(pedido_service):
    res_comum = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="tomate", quantidade=Decimal("20")),
        data_entrega=date(2026, 11, 4),
        data_referencia=date(2026, 10, 28),
    )
    res_cereja = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="tomate cereja", quantidade=Decimal("5")),
        data_entrega=date(2026, 11, 4),
        data_referencia=date(2026, 10, 28),
    )

    assert res_comum.variedade_preco == "tomate santa cruz"
    assert res_cereja.variedade_preco == "tomate cereja"
    assert [p.id for p in res_cereja.produtores_elegiveis] == ["P004"]


def test_produto_fora_de_safra_e_baixa_disponibilidade(pedido_service):
    mirtilo = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="mirtilo", quantidade=Decimal("5")),
        data_entrega=date(2026, 11, 5),
        data_referencia=date(2026, 10, 29),
    )
    caja = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="cajá", quantidade=Decimal("10")),
        data_entrega=date(2026, 11, 5),
        data_referencia=date(2026, 10, 29),
    )

    assert any(a.tipo == "fora_de_safra" for a in mirtilo.alertas)
    assert any(a.tipo == "baixa_disponibilidade" for a in caja.alertas)


def test_capacidade_hibrida_explicita_e_historica(pedido_service):
    frango = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="frango caipira", quantidade=Decimal("100")),
        data_entrega=date(2026, 11, 5),
        data_referencia=date(2026, 10, 29),
    )
    queijo = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="queijo coalho", quantidade=Decimal("200")),
        data_entrega=date(2026, 10, 29),
        data_referencia=date(2026, 10, 29),
    )

    assert frango.capacidade_referencia == Decimal("80")
    assert any(a.tipo == "quantidade_acima_capacidade" for a in frango.alertas)
    assert any(a.tipo == "restricao_sanitaria_sie" for a in frango.alertas)
    assert queijo.capacidade_referencia == Decimal("150")
    assert any(a.tipo == "quantidade_acima_capacidade" for a in queijo.alertas)


def test_leite_organico_inconsistente_gera_alerta(pedido_service):
    leite_org = pedido_service.validar_item(
        ItemPedidoEntrada(produto_informado="leite", quantidade=Decimal("20"), organico=True),
        data_entrega=date(2026, 11, 4),
        data_referencia=date(2026, 10, 28),
    )

    assert any(a.tipo == "certificacao_organica_indisponivel" for a in leite_org.alertas)
    assert leite_org.produtores_elegiveis == []


def test_divergencia_de_calendario_ped_001_e_002(pedido_service):
    a1 = pedido_service.verificar_divergencia_data("essa sexta (01/nov)", date(2026, 11, 1))
    a2 = pedido_service.verificar_divergencia_data("terça 04/nov", date(2026, 11, 4))
    ok = pedido_service.verificar_divergencia_data("sexta 30/out", date(2026, 10, 30))

    assert a1 is not None and a1.tipo == "data_inconsistente"
    assert a2 is not None and a2.tipo == "data_inconsistente"
    assert ok is None


def test_estruturar_pedido_desacoplado_de_tipo_e_urgencia(pedido_service):
    pedido = pedido_service.estruturar_pedido(
        [
            ItemPedidoEntrada(produto_informado="queijo coalho", quantidade=Decimal("30")),
            ItemPedidoEntrada(produto_informado="goiaba"),
        ],
        comprador="Restaurante Raízes",
        prazo_informado="essa sexta (01/nov)",
        data_entrega_prevista=date(2026, 11, 1),
        data_referencia=date(2026, 10, 28),
    )

    assert pedido.tipo is None
    assert pedido.urgencia is None
    assert "quantidade:goiaba" in pedido.informacoes_ausentes
    assert any(a.tipo == "data_inconsistente" for a in pedido.alertas)