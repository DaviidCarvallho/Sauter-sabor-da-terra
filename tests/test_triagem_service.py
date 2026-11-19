"""Testes da triagem determinística (prazo, urgência, tipo, ausências). Sem LLM."""

from datetime import date
from decimal import Decimal

import pytest

from models.pedido_model import ItemPedidoEntrada
from services.triagem_service import (
    TIPOS_PEDIDO,
    TriagemService,
    classificar_urgencia,
    resolver_prazo,
    validar_tipo,
)

QUARTA = date(2026, 10, 28)  # quarta-feira


def _item(produto, qtd=None, unidade=None, organico=False):
    return ItemPedidoEntrada(
        produto_informado=produto,
        quantidade=Decimal(str(qtd)) if qtd is not None else None,
        unidade_informada=unidade,
        organico=organico,
    )


@pytest.fixture(scope="module")
def triagem():
    return TriagemService()


# ---------- resolução de prazo ----------

@pytest.mark.parametrize(
    "expressao, esperado",
    [
        ("hoje", date(2026, 10, 28)),
        ("pra amanhã", date(2026, 10, 29)),
        ("depois de amanhã", date(2026, 10, 30)),
        ("pra sexta", date(2026, 10, 30)),
        ("sexta-feira", date(2026, 10, 30)),
        ("segunda", date(2026, 11, 2)),
        ("04/nov", date(2026, 11, 4)),
        ("8 de novembro", date(2026, 11, 8)),
        ("04/11/2026", date(2026, 11, 4)),
        ("sexta (01/nov)", date(2026, 11, 1)),  # data explícita vence o dia da semana
    ],
)
def test_prazo_resolvido(expressao, esperado):
    r = resolver_prazo(expressao, QUARTA)
    assert r.status == "resolvido" and r.data == esperado


def test_prazo_mesmo_dia_da_semana_e_ambiguo():
    assert resolver_prazo("quarta", QUARTA).status == "ambiguo"


@pytest.mark.parametrize("expressao", ["semana que vem", "o quanto antes", "próxima semana"])
def test_prazo_sem_dia_determinado_e_ambiguo(expressao):
    r = resolver_prazo(expressao, QUARTA)
    assert r.status == "ambiguo" and r.data is None


@pytest.mark.parametrize("expressao", ["", "qualquer coisa", "31/02"])
def test_prazo_nao_reconhecido(expressao):
    assert resolver_prazo(expressao, QUARTA).status == "nao_reconhecido"


def test_data_sem_ano_ja_passada_vai_para_o_ano_seguinte():
    assert resolver_prazo("05/jan", QUARTA).data == date(2027, 1, 5)


def test_quantidade_com_maco_nao_vira_mes():
    # "20 maços" não pode ser lido como "20 mar"
    assert resolver_prazo("20 maços de coentro", QUARTA).status == "nao_reconhecido"


# ---------- urgência e tipo ----------

@pytest.mark.parametrize(
    "dias, esperado", [(0, "urgente"), (2, "urgente"), (3, "normal"), (14, "normal"), (15, "planejado")]
)
def test_urgencia_por_dias(dias, esperado):
    entrega = date.fromordinal(QUARTA.toordinal() + dias)
    assert classificar_urgencia(entrega, QUARTA) == esperado


def test_urgencia_sinalizada_pelo_comprador_vence_o_prazo():
    assert classificar_urgencia(date(2026, 12, 20), QUARTA, sinalizada_pelo_comprador=True) == "urgente"


def test_urgencia_indefinida_sem_prazo_e_com_prazo_passado():
    assert classificar_urgencia(None, QUARTA) == "indefinida"
    assert classificar_urgencia(date(2026, 10, 1), QUARTA) == "indefinida"


def test_tipo_validado_e_normalizado():
    assert validar_tipo("Pedido Firme") == "pedido_firme"
    assert validar_tipo(None) is None
    assert set(TIPOS_PEDIDO) == {"pedido_firme", "cotacao", "fornecimento_recorrente", "nao_e_pedido"}


def test_tipo_invalido_levanta_erro():
    with pytest.raises(ValueError, match="inválido"):
        validar_tipo("compra_misteriosa")


# ---------- triagem completa com dados reais ----------

def test_pedido_completo(triagem):
    p = triagem.triar(
        [_item("queijo coalho", 30, "kg")], comprador="Restaurante Raízes",
        prazo_informado="sexta", data_referencia=QUARTA, tipo="pedido_firme",
    )
    assert p.data_entrega_prevista == date(2026, 10, 30)
    assert p.urgencia == "urgente" and p.tipo == "pedido_firme"
    assert p.itens[0].encontrado and p.itens[0].produtores_elegiveis
    assert p.informacoes_ausentes == []
    assert not [a for a in p.alertas if a.tipo == "quantidade_acima_capacidade"]


def test_pedido_incompleto_sem_quantidade_nem_comprador(triagem):
    p = triagem.triar([_item("goiaba")], prazo_informado="sexta", data_referencia=QUARTA)
    assert "comprador" in p.informacoes_ausentes
    assert "quantidade:goiaba" in p.informacoes_ausentes


def test_prazo_ambiguo_e_registrado(triagem):
    p = triagem.triar([_item("tomate", 100, "kg")], comprador="Mercado",
                      prazo_informado="semana que vem", data_referencia=QUARTA)
    assert "prazo_ambiguo" in p.informacoes_ausentes
    assert p.data_entrega_prevista is None and p.urgencia == "indefinida"


def test_sem_prazo_informado(triagem):
    p = triagem.triar([_item("tomate", 10, "kg")], comprador="Mercado", data_referencia=QUARTA)
    assert "prazo" in p.informacoes_ausentes


def test_prazo_no_passado(triagem):
    p = triagem.triar([_item("tomate", 10, "kg")], comprador="M",
                      prazo_informado="01/10/2026", data_referencia=QUARTA)
    assert "prazo_no_passado" in p.informacoes_ausentes


def test_produto_inexistente(triagem):
    p = triagem.triar([_item("jabuticaba", 3, "kg")], comprador="M",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert not p.itens[0].encontrado
    assert [a.tipo for a in p.alertas] == ["produto_nao_encontrado"]


def test_fora_de_safra(triagem):
    # Mirtilo: fora de safra em novembro (sazonalidade.csv)
    p = triagem.triar([_item("mirtilo", 5, "kg")], comprador="M",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert "fora_de_safra" in [a.tipo for a in p.alertas]


def test_quantidade_acima_da_capacidade(triagem):
    p = triagem.triar([_item("queijo coalho", 200, "kg")], comprador="Rede SuperBom",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert "quantidade_acima_capacidade" in [a.tipo for a in p.alertas]


def test_quantidade_sem_unidade_pede_esclarecimento(triagem):
    p = triagem.triar([_item("cebolinha", 10)], comprador="Raízes",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert "unidade:cebolinha" in p.informacoes_ausentes


def test_capacidade_nao_comprovada_e_informada(triagem):
    # Cebolinha não tem limite explícito nem lote histórico: não dá para afirmar capacidade.
    p = triagem.triar([_item("cebolinha", 10, "maço")], comprador="Raízes",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert p.itens[0].capacidade_referencia is None
    assert "capacidade_nao_comprovada:cebolinha" in p.informacoes_ausentes


def test_tipo_invalido_na_triagem(triagem):
    with pytest.raises(ValueError):
        triagem.triar([_item("tomate", 1, "kg")], comprador="M", data_referencia=QUARTA, tipo="x")


def test_triagem_nao_altera_o_pedido_original_do_servico(triagem):
    p = triagem.triar([_item("tomate", 5, "kg")], comprador="M",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    assert p.tipo is None  # tipo só é definido quando o agente o informa


# ---------- achados da bateria real com o Gemini ----------

def test_prazo_em_formato_iso_e_aceito():
    """O modelo reaproveita a data ISO devolvida pela nossa ferramenta (ex.: no follow-up)."""
    r = resolver_prazo("2026-11-20", QUARTA)
    assert r.status == "resolvido" and r.data == date(2026, 11, 20)
    assert resolver_prazo("entrega em 2026-02-30", QUARTA).status == "nao_reconhecido"


@pytest.mark.parametrize("produto, qtd, unidade", [
    ("coentro", 20, "maços"), ("coentro", 20, "maco"), ("ovos caipira", 100, "dúzias"),
    ("tomate", 10, "quilos"), ("alface", 50, "unidades"),
])
def test_unidade_equivalente_nao_gera_alerta_falso(triagem, produto, qtd, unidade):
    """Bug do pedido_service: sinônimos acentuados ('maço', 'dúzia') nunca igualavam a unidade oficial."""
    p = triagem.triar([_item(produto, qtd, unidade)], comprador="M", prazo_informado="04/nov",
                      data_referencia=QUARTA)
    assert "unidade_divergente" not in [a.tipo for a in p.alertas]
    assert p.itens[0].valor_estimado is not None
    assert not [x for x in p.informacoes_ausentes if x.startswith("conversao_unidade")]


def test_unidade_diferente_da_tabela_nao_gera_valor_enganoso(triagem):
    """'10 caixas' de goiaba não pode virar '10 kg x preço' sem fator de conversão."""
    p = triagem.triar([_item("goiaba", 10, "caixas"), _item("tomate", 5, "kg")], comprador="M",
                      prazo_informado="04/nov", data_referencia=QUARTA)
    goiaba, tomate = p.itens
    assert goiaba.unidade == "caixas" and goiaba.valor_estimado is None
    assert not goiaba.desconto_aplicado
    assert "conversao_unidade:goiaba" in p.informacoes_ausentes
    assert "unidade_divergente" in [a.tipo for a in p.alertas]
    # o total considera só os itens com valor confiável
    assert tomate.valor_estimado is not None and p.valor_total_estimado == tomate.valor_estimado
