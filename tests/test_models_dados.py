"""Testes dos models de dados (produtor, financeiro, produto e pedido bruto)."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from models.pedido_model import PedidoBruto
from models.produto_model import Lote, PrecoProduto, SazonalidadeProduto
from models.produtor_model import Produtor, Transacao
from repositories.storage_repository import carregar_modelos, ler_csv
from storage.local_storage import LocalStorage

DADOS = Path(__file__).resolve().parent.parent / "data"

SENSIVEIS = {
    "cpf", "produtor_cpf", "data_nascimento", "telefone", "email", "endereco",
    "chave_pix", "chave_pix_deposito", "banco", "agencia", "conta_corrente",
}

PRODUTOR = {
    "id": "P001", "nome_completo": "Maria", "cpf": "831.452.674-90",
    "municipio": "Garanhuns", "produtos": "goiaba,acerola,manga",
    "certificacao_organica": "sim", "validade_certificacao": "2027-06-15", "status": "ativo",
}

TRANSACAO = {
    "id_transacao": "FIN-2026-001", "data": "2026-09-02", "produtor_id": "P001",
    "produtor_nome": "Maria", "produtor_cpf": "831.452.674-90", "comprador": "Mercado",
    "tipo": "venda", "produto": "goiaba paluma", "quantidade_kg": "120",
    "valor_unitario": "4.50", "valor_total": "540.00", "forma_pagamento": "pix",
    "status_pagamento": "pago", "data_vencimento": "2026-10-02",
    "data_pagamento": "2026-10-01", "chave_pix_deposito": "831.452.674-90", "observacao": "",
}

LOTE = {
    "lote_id": "LOT-2026-0089", "data_colheita": "2026-09-01", "data_entrega": "2026-09-02",
    "produtor_id": "P003", "produtor_nome": "Cícero", "produtor_cpf": "723.016.498-55",
    "produto": "queijo coalho", "quantidade_kg": "45", "comprador": "Raízes",
    "pedido_id": "PED-2026-SEP-003", "temperatura_transporte_c": "8", "validade": "2026-10-02",
    "inspecao_visual": "aprovado", "observacao": "",
}


# ---------- Produtor ----------

def test_produtor_converte_valores_do_csv():
    p = Produtor.model_validate(PRODUTOR)
    assert p.nome == "Maria"
    assert p.produtos == ["goiaba", "acerola", "manga"]
    assert p.certificacao_organica is True
    assert p.validade_certificacao == date(2027, 6, 15)


def test_produtor_sem_certificacao_tem_validade_none():
    p = Produtor.model_validate({**PRODUTOR, "certificacao_organica": "nao", "validade_certificacao": ""})
    assert p.certificacao_organica is False and p.validade_certificacao is None


def test_produtor_nao_expoe_dados_sensiveis():
    p = Produtor.model_validate(PRODUTOR)
    assert not (SENSIVEIS & set(Produtor.model_fields))
    assert "831.452.674-90" not in p.model_dump_json()


@pytest.mark.parametrize(
    "campo,valor",
    [("certificacao_organica", "talvez"), ("status", "suspenso"), ("validade_certificacao", "15/06/2027")],
)
def test_produtor_rejeita_valores_invalidos(campo, valor):
    with pytest.raises(ValidationError):
        Produtor.model_validate({**PRODUTOR, campo: valor})


# ---------- Transacao ----------

def test_transacao_valida_e_sem_dados_sensiveis():
    t = Transacao.model_validate(TRANSACAO)
    assert t.quantidade == Decimal("120") and t.valor_total == Decimal("540.00")
    assert not (SENSIVEIS & set(Transacao.model_fields))
    assert "831.452.674-90" not in t.model_dump_json()


def test_transacao_pendente_sem_data_de_pagamento():
    t = Transacao.model_validate({**TRANSACAO, "status_pagamento": "pendente", "data_pagamento": ""})
    assert t.data_pagamento is None


@pytest.mark.parametrize(
    "alteracao",
    [
        {"valor_total": "541.00"},  # total não fecha com quantidade x unitário
        {"data_pagamento": ""},  # pago sem data de pagamento
        {"status_pagamento": "pendente"},  # pendente com data de pagamento
        {"status_pagamento": "atrasado"},  # status inexistente nos dados
        {"quantidade_kg": "0", "valor_total": "0"},
        {"valor_unitario": "-4.50", "valor_total": "-540.00"},
    ],
)
def test_transacao_rejeita_dados_inconsistentes(alteracao):
    with pytest.raises(ValidationError):
        Transacao.model_validate({**TRANSACAO, **alteracao})


# ---------- Lote ----------

def test_lote_temperatura_numerica_ou_ambiente():
    assert Lote.model_validate(LOTE).temperatura_transporte == 8
    assert Lote.model_validate({**LOTE, "temperatura_transporte_c": "ambiente"}).temperatura_transporte == "ambiente"
    with pytest.raises(ValidationError):
        Lote.model_validate({**LOTE, "temperatura_transporte_c": "frio"})


def test_lote_nao_expoe_cpf_e_rejeita_datas_incoerentes():
    lote = Lote.model_validate(LOTE)
    assert "723.016.498-55" not in lote.model_dump_json()
    with pytest.raises(ValidationError):
        Lote.model_validate({**LOTE, "data_colheita": "2026-09-05"})  # colheita depois da entrega
    with pytest.raises(ValidationError):
        Lote.model_validate({**LOTE, "validade": "2026-09-01"})  # vence antes da entrega


# ---------- Preço, sazonalidade e pedido bruto ----------

def test_preco_nd_vira_none():
    preco = PrecoProduto.model_validate({
        "produto": "pólen", "unidade": "kg", "preco_convencional": "n/d", "preco_organico": "120.00",
        "desconto_atacado_pct": "0", "volume_minimo_atacado_kg": "0", "observacao": "",
    })
    assert preco.preco_convencional is None and preco.preco_organico == Decimal("120.00")


@pytest.mark.parametrize("alteracao", [{"unidade": "caixa"}, {"desconto_atacado_pct": "120"}])
def test_preco_rejeita_valores_invalidos(alteracao):
    base = {
        "produto": "x", "unidade": "kg", "preco_convencional": "1.00", "preco_organico": "n/d",
        "desconto_atacado_pct": "0", "volume_minimo_atacado_kg": "0",
    }
    with pytest.raises(ValidationError):
        PrecoProduto.model_validate({**base, **alteracao})


def test_sazonalidade_exige_12_meses_e_niveis_validos():
    meses = {m: "alta" for m in "jan fev mar abr mai jun jul ago set out nov dez".split()}
    assert SazonalidadeProduto.model_validate({"produto": "manga tommy", **meses}).nov == "alta"
    with pytest.raises(ValidationError):
        SazonalidadeProduto.model_validate({"produto": "x", **{**meses, "nov": "média"}})
    meses.pop("dez")
    with pytest.raises(ValidationError):
        SazonalidadeProduto.model_validate({"produto": "x", **meses})


def test_pedido_bruto_converte_data_e_valida_canal():
    base = {
        "id": "PED-2026-001", "data_recebimento": "2026-10-28T09:15:00", "canal": "email",
        "remetente": "a@b.com", "comprador": "Fulano", "mensagem_original": "oi", "status": "pendente",
    }
    assert PedidoBruto.model_validate(base).data_recebimento == datetime(2026, 10, 28, 9, 15)
    with pytest.raises(ValidationError):
        PedidoBruto.model_validate({**base, "canal": "telegrama"})


# ---------- Arquivos reais ----------

@pytest.mark.skipif(not (DADOS / "sazonalidade.csv").exists(), reason="data/ sem os arquivos reais")
def test_sazonalidade_e_precos_reais_sao_validos():
    storage = LocalStorage(DADOS)
    saz = carregar_modelos(
        "sazonalidade.csv", ler_csv("sazonalidade.csv", storage), SazonalidadeProduto, campo_id="produto"
    )
    precos = carregar_modelos(
        "tabela_precos_outubro_2026.csv",
        ler_csv("tabela_precos_outubro_2026.csv", storage),
        PrecoProduto,
        campo_id="produto",
    )
    assert len(saz) == 50 and len(precos) == 53
    assert {s.produto: s.nov for s in saz}["cajá"] == "baixa"