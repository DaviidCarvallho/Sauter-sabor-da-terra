"""Testes das ferramentas dos agentes (sem Gemini)."""

import ast
from datetime import date
from pathlib import Path

import pytest
from google.adk.tools import FunctionTool

import agents.tools as tools
from agents.tools import (
    FERRAMENTAS_PEDIDOS,
    ItemTriagem,
    consultar_pedido_recebido,
    obter_data_atual,
    resolver_prazo_pedido,
    triar_pedido,
)

REF = "2026-10-28"  # quarta-feira


def test_todas_as_ferramentas_geram_declaracao_para_o_adk():
    for func in FERRAMENTAS_PEDIDOS:
        decl = FunctionTool(func)._get_declaration()
        assert decl.name == func.__name__
        assert decl.description and "Args" not in (decl.description or "").split("\n")[0]


def test_schema_de_triar_pedido_expoe_itens_tipados():
    schema = FunctionTool(triar_pedido)._get_declaration().parameters_json_schema
    assert "itens" in schema["properties"] and "ItemTriagem" in schema["$defs"]
    assert "itens" not in schema.get("required", [])  # tolerante a omissão (ver tools.py)


def test_tools_nao_acessam_repositorios_nem_arquivos():
    """Contrato: tools são adaptadores; só services/models/utils."""
    arvore = ast.parse(Path(tools.__file__).read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and no.module:
            importados.add(no.module.split(".")[0])
        elif isinstance(no, ast.Import):
            importados.update(a.name.split(".")[0] for a in no.names)
    assert importados.isdisjoint({"repositories", "storage", "rag", "chromadb", "csv", "json"})


def test_obter_data_atual(monkeypatch):
    class FalsaData(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 28)

    monkeypatch.setattr(tools, "date", FalsaData)
    r = obter_data_atual()
    assert r == {"status": "sucesso", "data": "2026-10-28", "dia_semana": "quarta-feira"}


def test_resolver_prazo_resolvido():
    r = resolver_prazo_pedido("pra sexta", REF)
    assert r["status"] == "sucesso" and r["resultado"] == "resolvido" and r["data"] == "2026-10-30"


def test_resolver_prazo_ambiguo_nao_inventa_data():
    r = resolver_prazo_pedido("semana que vem", REF)
    assert r["resultado"] == "ambiguo" and r["data"] is None


def test_resolver_prazo_referencia_invalida():
    assert resolver_prazo_pedido("sexta", "28/10/2026")["status"] == "erro"


def test_triar_pedido_completo():
    r = triar_pedido(
        [ItemTriagem(produto="queijo coalho", quantidade=30, unidade="kg")],
        comprador="Restaurante Raízes", prazo="sexta", tipo="pedido_firme", data_referencia=REF,
    )
    assert r["status"] == "sucesso"
    pedido = r["pedido"]
    assert pedido["urgencia"] == "urgente" and pedido["tipo"] == "pedido_firme"
    assert pedido["data_entrega_prevista"] == "2026-10-30"
    assert r["prazo"]["resultado"] == "resolvido"


def test_triar_pedido_nao_inventa_quantidade():
    r = triar_pedido([ItemTriagem(produto="goiaba", unidade="caixas")], comprador="X", prazo="sexta",
                     data_referencia=REF)
    assert r["pedido"]["itens"][0]["quantidade"] is None
    assert "quantidade:goiaba" in r["pedido"]["informacoes_ausentes"]


def test_triar_pedido_resultado_estruturado_compativel_com_contrato():
    r = triar_pedido([ItemTriagem(produto="mirtilo", quantidade=5, unidade="kg")], comprador="M",
                     prazo="04/nov", data_referencia=REF)
    pedido = r["pedido"]
    for campo in ("comprador", "prazo_informado", "itens", "informacoes_ausentes", "alertas",
                  "tipo", "urgencia"):
        assert campo in pedido
    assert pedido["alertas"][0]["tipo"] == "fora_de_safra"
    assert {"tipo", "mensagem", "severidade"} <= set(pedido["alertas"][0])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"itens": []},
        {"itens": [ItemTriagem(produto="tomate", quantidade=1)], "tipo": "inexistente"},
        {"itens": [ItemTriagem(produto="tomate", quantidade=1)], "data_referencia": "ontem"},
        {"itens": [ItemTriagem(produto="   ")]},
    ],
)
def test_triar_pedido_erro_de_entrada_vira_dicionario_de_erro(kwargs):
    r = triar_pedido(**kwargs)
    assert r["status"] == "erro" and r["mensagem"]


def test_triar_pedido_quantidade_invalida_e_erro_controlado():
    r = triar_pedido([ItemTriagem(produto="tomate", quantidade=-5)], comprador="M", data_referencia=REF)
    assert r["status"] == "erro"


def test_falha_de_leitura_de_dados_e_controlada_sem_vazar_detalhes(monkeypatch):
    class Quebrado:
        def triar(self, *a, **k):
            raise FileNotFoundError("C:\\segredo\\caminho\\produtores.csv")

    monkeypatch.setattr(tools, "get_triagem_service", lambda: Quebrado())
    r = triar_pedido([ItemTriagem(produto="tomate", quantidade=1)], comprador="M", data_referencia=REF)
    assert r["status"] == "erro"
    assert "segredo" not in r["mensagem"] and "csv" not in r["mensagem"]


def test_falha_inesperada_propaga_para_o_adk(monkeypatch):
    class Bug:
        def triar(self, *a, **k):
            raise RuntimeError("bug")

    monkeypatch.setattr(tools, "get_triagem_service", lambda: Bug())
    with pytest.raises(RuntimeError):
        triar_pedido([ItemTriagem(produto="tomate", quantidade=1)], comprador="M", data_referencia=REF)


def test_consultar_pedido_mascara_cpf_e_traz_data_de_referencia():
    r = consultar_pedido_recebido("ped-2026-015")
    assert r["status"] == "sucesso" and r["pedido_id"] == "PED-2026-015"
    assert "432.198.765-01" not in r["mensagem_original"] and "[CPF omitido]" in r["mensagem_original"]
    assert r["data_referencia"] == "2026-10-30"


def test_consultar_pedido_codigo_invalido_e_inexistente():
    assert consultar_pedido_recebido("123")["status"] == "erro"
    r = consultar_pedido_recebido("PED-2026-999")
    assert r["status"] == "erro" and "não encontrado" in r["mensagem"]


@pytest.mark.parametrize("func", FERRAMENTAS_PEDIDOS, ids=lambda f: f.__name__)
def test_ferramentas_toleram_argumentos_omitidos_pelo_modelo(func):
    """Regressão (teste real com o Gemini): resolver_prazo_pedido() chamado sem 'expressao' gerava
    TypeError e derrubava a conversa. Toda ferramenta deve responder sem exceção quando o modelo
    omite argumentos."""
    import inspect

    assert all(p.default is not inspect.Parameter.empty for p in inspect.signature(func).parameters.values())
    resultado = func()
    assert resultado["status"] in {"sucesso", "erro"}


@pytest.mark.parametrize("func", [resolver_prazo_pedido, triar_pedido, consultar_pedido_recebido])
def test_argumento_ausente_devolve_erro_orientando_o_modelo(func):
    r = func()
    assert r["status"] == "erro" and r["mensagem"]
