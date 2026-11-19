"""Valida os eval sets do ADK (evals/) e reexecuta a parte determinística da triagem (sem LLM)."""

import json
from datetime import date
from pathlib import Path

import pytest
from google.adk.evaluation.eval_set import EvalSet

import agents.tools as tools

RAIZ = Path(__file__).resolve().parent.parent
EVALS = RAIZ / "evals"
ARQUIVOS = sorted(EVALS.glob("*.evalset.json"))
ESPECIALISTAS = {"pedidos_agent", "documentos_agent", "produtores_agent"}
FERRAMENTAS = {f.__name__ for f in (*tools.FERRAMENTAS_PEDIDOS, *tools.FERRAMENTAS_DOCUMENTOS, *tools.FERRAMENTAS_PRODUTORES)}


def _carregar(arquivo: Path) -> EvalSet:
    return EvalSet.model_validate_json(arquivo.read_text(encoding="utf-8"))


def test_ha_tres_conjuntos_e_configuracao():
    assert [a.name for a in ARQUIVOS] == ["documentos.evalset.json", "pedidos.evalset.json", "produtores.evalset.json"]
    assert "tool_trajectory_avg_score" in json.loads((EVALS / "test_config.json").read_text(encoding="utf-8"))["criteria"]


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.name)
def test_formato_e_trajetoria_referenciam_ferramentas_existentes(arquivo):
    conjunto = _carregar(arquivo)
    assert conjunto.eval_cases
    for caso in conjunto.eval_cases:
        assert caso.conversation and caso.conversation[0].user_content.parts[0].text
        usos = caso.conversation[0].intermediate_data.tool_uses
        assert {u.name for u in usos} <= ESPECIALISTAS | FERRAMENTAS, caso.eval_id


def _data_do_pedido(pedido_id: str) -> date:
    pedidos = json.loads((RAIZ / "data" / "pedidos.json").read_text(encoding="utf-8"))
    return date.fromisoformat(next(p for p in pedidos if p["id"] == pedido_id)["data_recebimento"][:10])


def _casos_de_triagem():
    conjunto = _carregar(EVALS / "pedidos.evalset.json")
    return [c for c in conjunto.eval_cases if (c.final_session_state or {}).get("triagem_esperada")]


@pytest.mark.parametrize("caso", _casos_de_triagem(), ids=lambda c: c.eval_id)
def test_triagem_deterministica_reproduz_o_esperado(caso, monkeypatch):
    monkeypatch.setattr(tools, "_hoje", lambda: _data_do_pedido(caso.eval_id))
    chamada = next(u for u in caso.conversation[0].intermediate_data.tool_uses if u.name == "triar_pedido")
    args = dict(chamada.args)
    args["itens"] = [tools.ItemTriagem(**i) for i in args["itens"]]
    resultado = tools.triar_pedido(**args)

    assert resultado["status"] == "sucesso"
    pedido = resultado["pedido"]
    esperado = caso.final_session_state["triagem_esperada"]
    assert pedido["tipo"] == esperado["tipo"]
    assert pedido["urgencia"] == esperado["urgencia"]
    assert sorted({a["tipo"] for i in pedido["itens"] for a in i["alertas"]}) == esperado["alertas"]
    assert pedido["informacoes_ausentes"] == esperado["informacoes_ausentes"]
