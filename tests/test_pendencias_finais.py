"""Rastreabilidade de lotes (serviço), conversão dúzia<->unidade e alertas estruturados do chat."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from agents.agent import construir_root_agent
from main import app
from models.pedido_model import ItemPedidoEntrada
from repositories.lote_repository import LoteRepository
from services.chat_service import ChatService, get_chat_service
from services.produtor_service import ProdutorService
from services.triagem_service import TriagemService, converter_duzia_unidade
from tests.llm_simulado import ScriptedLlm, chamar, texto

REF = date(2026, 10, 28)


# --- rastreabilidade de lotes no nível de serviço -------------------------------------------------


def test_dossie_traz_somente_lotes_do_proprio_produtor_com_rastreio_completo():
    todos = LoteRepository().listar()
    dossie = ProdutorService().obter_dossie("P001", data_referencia=REF)

    esperados = {lote.lote_id for lote in todos if lote.produtor_id == "P001"}
    assert esperados, "a base real deve ter lotes do P001"
    assert {lote.lote_id for lote in dossie.lotes} == esperados
    for lote in dossie.lotes:
        assert lote.produtor_id == "P001"
        assert lote.pedido_id and lote.comprador and lote.produto
        assert lote.data_colheita <= lote.data_entrega
        assert lote.unidade  # enriquecida pelo serviço com a unidade da tabela de preços


def test_lote_rastreia_ate_o_pedido_e_o_comprador():
    lote = LoteRepository().buscar_por_id("LOT-2026-0091")
    assert lote is not None
    assert (lote.produtor_id, lote.pedido_id, lote.comprador) == ("P001", "PED-2026-SEP-005", "Mercado Bom Preço")


def test_produtor_sem_lotes_devolve_lista_vazia():
    ids_com_lote = {lote.produtor_id for lote in LoteRepository().listar()}
    sem_lote = next(
        (p.id for p in ProdutorService()._produtor_repo.listar() if p.id not in ids_com_lote), None
    )
    if sem_lote is None:
        pytest.skip("todos os produtores da base têm lotes")
    assert ProdutorService().obter_dossie(sem_lote, data_referencia=REF).lotes == []


# --- conversão de unidade -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("qtd", "informada", "oficial", "esperado"),
    [
        (Decimal("2"), "dúzias", "unidade", (Decimal("24"), "unidade")),
        (Decimal("2"), "duzia", "unidade", (Decimal("24"), "unidade")),
        (Decimal("24"), "unidades", "dúzia", (Decimal("2"), "dúzia")),
        (Decimal("5"), "maços", "kg", None),
        (Decimal("5"), "caixas", "kg", None),
        (Decimal("5"), "kg", "kg", None),
        (None, "dúzias", "unidade", None),
        (Decimal("5"), None, "unidade", None),
    ],
)
def test_converter_duzia_unidade(qtd, informada, oficial, esperado):
    assert converter_duzia_unidade(qtd, informada, oficial) == esperado


def test_triagem_converte_duzia_para_unidade_e_estima_valor():
    p = TriagemService().triar(
        [ItemPedidoEntrada(produto_informado="alface", quantidade=Decimal("5"), unidade_informada="dúzias")],
        data_referencia=REF,
    )
    item = p.itens[0]
    assert item.quantidade == Decimal("60") and item.unidade == "unidade"
    assert item.valor_estimado is not None
    assert "conversao_unidade_aplicada" in [a.tipo for a in item.alertas]
    assert "unidade_divergente" not in [a.tipo for a in item.alertas]
    assert not [x for x in p.informacoes_ausentes if x.startswith("conversao_unidade")]


def test_triagem_nao_converte_unidade_sem_fator_e_pede_informacao():
    p = TriagemService().triar(
        [ItemPedidoEntrada(produto_informado="goiaba paluma", quantidade=Decimal("3"), unidade_informada="caixas")],
        data_referencia=REF,
    )
    assert p.itens[0].valor_estimado is None
    assert "conversao_unidade:goiaba paluma" in p.informacoes_ausentes


# --- alertas estruturados no chat -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def _limpa_overrides():
    yield
    app.dependency_overrides.clear()


def _chat(itens, mensagem):
    llm = ScriptedLlm(respostas=[
        chamar("pedidos_agent", request=mensagem),
        chamar("triar_pedido", itens=itens, comprador="Mercado Bom Preço", prazo="sexta-feira",
               tipo="pedido_firme", data_referencia="2026-10-28"),
        texto("Triagem feita."),
        texto("Triagem concluída com alertas."),
    ])
    servico = ChatService(agente=construir_root_agent(llm))
    app.dependency_overrides[get_chat_service] = lambda: servico
    return TestClient(app).post("/api/chat", json={"user_id": "u1", "message": mensagem})


def test_chat_devolve_alertas_estruturados_do_codigo():
    r = _chat([{"produto": "morango", "quantidade": 50, "unidade": "kg"}], "50 kg de morango pra sexta")
    assert r.status_code == 200
    alertas = r.json()["alerts"]
    assert alertas, "morango fora de safra em outubro deve gerar ao menos um alerta"
    for a in alertas:
        assert set(a) == {"tipo", "severidade", "mensagem", "produto"}
    assert all(a["mensagem"] for a in alertas)


def test_chat_sem_pedido_devolve_alertas_vazios():
    llm = ScriptedLlm(respostas=[texto("Olá! Como posso ajudar?")])
    servico = ChatService(agente=construir_root_agent(llm))
    app.dependency_overrides[get_chat_service] = lambda: servico
    r = TestClient(app).post("/api/chat", json={"user_id": "u1", "message": "oi"})
    assert r.status_code == 200 and r.json()["alerts"] == []
