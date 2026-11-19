"""Agente de Produtores: ferramentas (dados reais), privacidade, prompt e fluxo ponta a ponta (sem Gemini)."""

import inspect
import json

import pytest
from fastapi.testclient import TestClient
from google.adk.tools import FunctionTool

import agents.tools as tools
from agents import prompts
from agents.agent import construir_root_agent
from agents.subagents.produtores_agent import criar_produtores_agent
from main import app
from services.chat_service import ChatService, get_chat_service
from tests.llm_simulado import ScriptedLlm, chamar, respostas_de_ferramenta_na_requisicao, texto

REF = "2026-10-30"
PROIBIDOS = ("cpf", "telefone", "agencia", "agência", "pix", "0437", "@")  # nada sensível na saída


# ---------- ferramentas ----------

@pytest.mark.parametrize("func", tools.FERRAMENTAS_PRODUTORES, ids=lambda f: f.__name__)
def test_ferramentas_toleram_argumentos_omitidos(func):
    assert all(p.default is not inspect.Parameter.empty for p in inspect.signature(func).parameters.values())
    assert func()["status"] in {"sucesso", "erro"}


@pytest.mark.parametrize("func", [tools.consultar_produtor, tools.resumo_produtor, tools.dados_notificacao_produtor])
def test_sem_produtor_devolve_erro_orientador(func):
    r = func()
    assert r["status"] == "erro" and "produtor" in r["mensagem"].lower()


def test_consultar_por_id_e_por_nome():
    por_id = tools.consultar_produtor("P003")["produtor"]
    por_nome = tools.consultar_produtor("Cícero")["produtor"]
    assert por_id["id"] == por_nome["id"] == "P003"
    assert {"nome", "municipio", "produtos", "certificacao_organica", "situacao"} <= set(por_id)


def test_produtor_inexistente():
    r = tools.consultar_produtor("zzz")
    assert r["status"] == "erro" and "não encontrado" in r["mensagem"]
    assert tools.resumo_produtor("P999")["status"] == "erro"


def test_resumo_traz_totais_calculados_pelo_servico():
    r = tools.resumo_produtor("P001", data_referencia=REF)
    assert r["status"] == "sucesso"
    resumo = r["resumo"]
    assert resumo["produtor_id"] == "P001" and resumo["data_referencia"] == REF
    for campo in ("total_vendas", "total_pago", "total_pendente", "total_em_atraso", "produtos_vendidos"):
        assert campo in resumo


def test_resumo_nao_vaza_dados_sensiveis_do_pedido_relacionado():
    """PED-2026-012 cita a conta bancária da produtora no texto original."""
    r = tools.resumo_produtor("P001", data_referencia=REF)
    assert r["resumo"]["pedidos_relacionados"], "o PED-2026-012 deveria estar relacionado à P001"
    saida = json.dumps(r, ensure_ascii=False).lower()
    assert not [p for p in PROIBIDOS if p in saida]
    assert "mensagem_original" not in saida


def test_notificacao_traz_pendencias_enxutas():
    r = tools.dados_notificacao_produtor("P003", REF)
    assert r["status"] == "sucesso"
    dados = r["dados"]
    assert dados["quantidade_pendencias"] == len(dados["itens_pendentes"]) > 0
    assert set(dados["itens_pendentes"][0]) == {
        "id_transacao", "data", "comprador", "produto", "quantidade", "unidade",
        "valor_total", "status_pagamento", "data_vencimento"}  # sem forma de pagamento nem observações
    assert not [p for p in PROIBIDOS if p in json.dumps(r, ensure_ascii=False).lower()]


def test_data_invalida_e_erro_controlado():
    assert tools.resumo_produtor("P001", data_inicio="ontem")["status"] == "erro"


def test_falha_de_leitura_e_controlada_sem_vazar_detalhes(monkeypatch):
    class Quebrado:
        def gerar_relatorio_produtor(self, *a, **k):
            raise OSError("caminho interno secreto")

    monkeypatch.setattr(tools, "get_relatorio_service", lambda: Quebrado())
    r = tools.resumo_produtor("P001")
    assert r["status"] == "erro" and "secreto" not in r["mensagem"]


def test_schemas_nao_expoem_parametros_internos():
    props = FunctionTool(tools.resumo_produtor)._get_declaration().parameters_json_schema["properties"]
    assert set(props) == {"produtor", "data_inicio", "data_fim", "data_referencia"}


# ---------- prompt e agente ----------

def test_prompt_de_produtores():
    t = prompts.INSTRUCAO_PRODUTORES
    assert "{" not in t and "}" not in t
    for ferramenta in tools.FERRAMENTAS_PRODUTORES:
        assert ferramenta.__name__ in t
    assert "NÃO autentica" in t and "meu saldo" in t           # recusa consulta em nome próprio
    assert "Rascunho para revisão da equipe; não enviado." in t  # notificação nunca é enviada
    assert "Nunca informe nem peça CPF" in t


def test_orquestrador_nao_aciona_produtores_para_consulta_pessoal():
    texto_orq = prompts.instrucao_orquestrador({"produtores_agent": prompts.DESCRICAO_PRODUTORES})
    assert "NÃO chame o especialista de produtores" in texto_orq


def test_agente_expoe_apenas_ferramentas_de_produtores():
    nomes = sorted(f.__name__ for f in criar_produtores_agent(ScriptedLlm()).tools)
    assert nomes == sorted(f.__name__ for f in tools.FERRAMENTAS_PRODUTORES)


# ---------- fluxo ponta a ponta ----------

@pytest.fixture(autouse=True)
def _limpa():
    yield
    app.dependency_overrides.clear()


def _cliente(llm):
    servico = ChatService(agente=construir_root_agent(llm))
    app.dependency_overrides[get_chat_service] = lambda: servico
    return TestClient(app)


def test_resumo_de_produtor_usa_numeros_reais_dos_servicos():
    llm = ScriptedLlm(respostas=[
        chamar("produtores_agent", request="Resumo de vendas e pendências do produtor P003."),
        chamar("resumo_produtor", produtor="P003", data_referencia=REF),
        texto("Resumo do P003 na data 2026-10-30."),
        texto("Resumo do produtor P003 (30/10/2026)."),
    ])
    r = _cliente(llm).post("/api/chat", json={"user_id": "u1", "message": "Resumo do produtor P003"})
    assert r.status_code == 200 and r.json()["agents_used"] == ["produtores_agent"]
    resumo = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["resumo_produtor"][0]["resumo"]
    assert resumo["produtor_id"] == "P003" and float(resumo["total_vendas"]) > 0  # número vindo do serviço


def test_notificacao_e_rascunho_com_dados_do_servico():
    llm = ScriptedLlm(respostas=[
        chamar("produtores_agent", request="Redija uma notificação de pendências para o produtor P003."),
        chamar("dados_notificacao_produtor", produtor="P003", data_referencia=REF),
        texto("Olá, Cícero! ... Rascunho para revisão da equipe; não enviado."),
        texto("Segue o rascunho. Rascunho para revisão da equipe; não enviado."),
    ])
    r = _cliente(llm).post("/api/chat", json={"message": "Redija um aviso para o produtor P003"})
    assert r.status_code == 200 and "não enviado" in r.json()["answer"]
    dados = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["dados_notificacao_produtor"][0]["dados"]
    assert dados["quantidade_pendencias"] > 0
