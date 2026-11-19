"""Orquestração: root_agent, delegação por AgentTool, trajetória e sessão (LLM simulado, sem custo)."""

import sys
import types as pytypes

import pytest
from google.adk import Agent
from google.adk.runners import Runner
from google.adk.tools import AgentTool

import agents.agent as agente_mod
import agents.tools as tools
from agents.agent import construir_root_agent
from agents.subagents.pedidos_agent import criar_pedidos_agent
from tests.llm_simulado import (
    ScriptedLlm,
    chamadas_de_ferramenta,
    chamar,
    conversar,
    instrucao_da_requisicao,
    nomes_das_ferramentas,
    nova_sessao,
    respostas_de_ferramenta_na_requisicao,
    texto,
    textos_do_usuario,
)

MSG = "Bom dia, o Mercado Bom Preço precisa de 100 kg de tomate para sexta-feira."
ITENS_TOMATE = [{"produto": "tomate", "quantidade": 100, "unidade": "kg"}]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _montar(llm):
    servico, sessao = await nova_sessao()
    runner = Runner(app_name="teste", agent=construir_root_agent(llm), session_service=servico)
    return runner, sessao


def _roteiro_pedido(final="Resposta final."):
    return [
        chamar("pedidos_agent", request=MSG),
        chamar("obter_data_atual"),
        chamar("triar_pedido", itens=ITENS_TOMATE, comprador="Mercado Bom Preço",
               prazo="sexta-feira", tipo="pedido_firme", data_referencia="2026-10-28"),
        texto("Triagem: tomate 100 kg, entrega 30/10 (sexta-feira)."),
        texto(final),
    ]


# ---------- estrutura do root_agent (síncrono) ----------

def test_root_agent_registra_especialistas_como_agent_tool():
    root = construir_root_agent(ScriptedLlm())
    assert all(isinstance(t, AgentTool) for t in root.tools)
    assert [t.name for t in root.tools] == ["pedidos_agent", "documentos_agent"]
    assert "pedidos_agent" in root.instruction and "documentos_agent" in root.instruction
    assert not root.sub_agents  # contrato: AgentTool, não sub_agents


def test_root_agent_do_modulo_existe_para_adk_web():
    assert isinstance(agente_mod.root_agent, Agent)


def test_especialista_ausente_nao_derruba_o_orquestrador(monkeypatch):
    monkeypatch.setattr(agente_mod, "ESPECIALISTAS", (
        ("agents.subagents.pedidos_agent", "criar_pedidos_agent"),
        ("agents.subagents.produtores_agent", "criar_produtores_agent"),  # ainda não implementado
    ))
    root = construir_root_agent(ScriptedLlm())
    assert [t.name for t in root.tools] == ["pedidos_agent"]


def test_especialista_novo_e_registrado_pelo_contrato_de_plugin(monkeypatch):
    """Rawan/Arthur só precisam expor criar_<nome>_agent(model) no módulo deles."""
    modulo = pytypes.ModuleType("agents.subagents.especialista_falso")
    modulo.criar_falso_agent = lambda model=None: Agent(
        name="documentos_agent", model=model, description="Responde sobre documentos com fontes.",
        instruction="Responda com fontes.")
    monkeypatch.setitem(sys.modules, "agents.subagents.especialista_falso", modulo)
    monkeypatch.setattr(agente_mod, "ESPECIALISTAS", (
        ("agents.subagents.pedidos_agent", "criar_pedidos_agent"),
        ("agents.subagents.especialista_falso", "criar_falso_agent"),
    ))
    root = construir_root_agent(ScriptedLlm())
    assert [t.name for t in root.tools] == ["pedidos_agent", "documentos_agent"]
    assert "Responde sobre documentos" in root.instruction


def test_agente_de_pedidos_isolado_expoe_apenas_ferramentas_de_pedidos():
    agente = criar_pedidos_agent(ScriptedLlm())
    assert sorted(f.__name__ for f in agente.tools) == sorted(f.__name__ for f in tools.FERRAMENTAS_PEDIDOS)


# ---------- delegação e trajetória (assíncrono) ----------

@pytest.mark.anyio
async def test_pedido_e_delegado_ao_agente_de_pedidos_e_ferramenta_real_e_usada():
    llm = ScriptedLlm(respostas=_roteiro_pedido("Tomate: 100 kg para sexta, 30/10."))
    runner, sessao = await _montar(llm)
    final, eventos = await conversar(runner, "u1", sessao.id, MSG)

    assert final == "Tomate: 100 kg para sexta, 30/10."
    assert not llm.respostas, "o roteiro deveria ser consumido por completo"
    # O orquestrador só chama o especialista; não chama ferramentas de negócio.
    assert [(a, n) for a, n, _ in chamadas_de_ferramenta(eventos)] == [
        ("assistente_sabor_da_terra", "pedidos_agent")]
    # Trajetória do especialista: a 4ª requisição já traz os resultados reais das ferramentas.
    resultados = respostas_de_ferramenta_na_requisicao(llm.requisicoes[3])
    assert list(resultados) == ["obter_data_atual", "triar_pedido"]
    assert resultados["triar_pedido"][0]["status"] == "sucesso"
    pedido = resultados["triar_pedido"][0]["pedido"]
    assert pedido["data_entrega_prevista"] == "2026-10-30" and pedido["urgencia"] == "urgente"
    assert pedido["itens"][0]["produto_normalizado"] == "tomate"


@pytest.mark.anyio
async def test_chamadas_nao_ultrapassam_o_necessario():
    llm = ScriptedLlm(respostas=_roteiro_pedido())
    runner, sessao = await _montar(llm)
    await conversar(runner, "u1", sessao.id, MSG)
    assert len(llm.requisicoes) == 5  # root, esp, esp, esp, root: sem laços nem repetições


@pytest.mark.anyio
async def test_saudacao_nao_aciona_especialistas():
    llm = ScriptedLlm(respostas=[texto("Olá! Posso ajudar com pedidos, documentos e produtores.")])
    runner, sessao = await _montar(llm)
    final, eventos = await conversar(runner, "u1", sessao.id, "Oi, tudo bem?")
    assert chamadas_de_ferramenta(eventos) == []
    assert len(llm.requisicoes) == 1 and final.startswith("Olá")


@pytest.mark.anyio
async def test_requisicao_do_orquestrador_contem_instrucao_e_apenas_ferramentas_de_agente():
    llm = ScriptedLlm(respostas=[texto("ok")])
    runner, sessao = await _montar(llm)
    await conversar(runner, "u1", sessao.id, "Oi")
    req = llm.requisicoes[0]
    assert nomes_das_ferramentas(req) == ["documentos_agent", "pedidos_agent"]
    assert "Sabor da Terra" in instrucao_da_requisicao(req)


@pytest.mark.anyio
async def test_especialista_recebe_somente_o_texto_da_chamada_sem_historico():
    llm = ScriptedLlm(respostas=[
        texto("Olá!"),
        chamar("pedidos_agent", request="Pedido: 100 kg de tomate para sexta, Mercado Bom Preço."),
        texto("Triagem feita."),
        texto("Resposta final."),
    ])
    runner, sessao = await _montar(llm)
    await conversar(runner, "u1", sessao.id, "Meu segredo: mensagem anterior confidencial.")
    await conversar(runner, "u1", sessao.id, "Quero 100 kg de tomate")
    req_especialista = llm.requisicoes[2]
    assert textos_do_usuario(req_especialista) == [
        "Pedido: 100 kg de tomate para sexta, Mercado Bom Preço."]
    assert "confidencial" not in str(req_especialista.contents)


# ---------- sessão ----------

@pytest.mark.anyio
async def test_continuidade_de_sessao_e_isolamento_entre_sessoes():
    servico, s1 = await nova_sessao()
    s2 = await servico.create_session(app_name="teste", user_id="u2")
    llm = ScriptedLlm(respostas=[texto("a"), texto("b"), texto("c")])
    runner = Runner(app_name="teste", agent=construir_root_agent(llm), session_service=servico)

    await conversar(runner, "u1", s1.id, "Primeira mensagem de u1")
    await conversar(runner, "u1", s1.id, "Segunda mensagem de u1")
    await conversar(runner, "u2", s2.id, "Mensagem de u2")

    assert "Primeira mensagem de u1" in textos_do_usuario(llm.requisicoes[1])  # contexto mantido
    assert "Primeira mensagem de u1" not in str(llm.requisicoes[2].contents)    # outra sessão: isolada


# ---------- falhas e pendências ----------

@pytest.mark.anyio
async def test_falha_controlada_de_ferramenta_chega_ao_modelo_como_erro(monkeypatch):
    class Quebrado:
        def triar(self, *a, **k):
            raise FileNotFoundError("C:\\interno\\produtores.csv")

    monkeypatch.setattr(tools, "get_triagem_service", lambda: Quebrado())
    llm = ScriptedLlm(respostas=_roteiro_pedido("Não consegui consultar os dados agora."))
    runner, sessao = await _montar(llm)
    final, _ = await conversar(runner, "u1", sessao.id, MSG)

    resultado = respostas_de_ferramenta_na_requisicao(llm.requisicoes[3])["triar_pedido"][0]
    assert resultado["status"] == "erro" and "interno" not in resultado["mensagem"]
    assert final == "Não consegui consultar os dados agora."


@pytest.mark.anyio
async def test_pedido_sem_quantidade_chega_ao_modelo_com_pendencia():
    llm = ScriptedLlm(respostas=[
        chamar("pedidos_agent", request="Quero umas caixas de goiaba pra sexta"),
        chamar("triar_pedido", itens=[{"produto": "goiaba", "unidade": "caixas"}], prazo="sexta",
               data_referencia="2026-10-28"),
        texto("Quantas caixas de goiaba?"),
        texto("Quantas caixas de goiaba você precisa?"),
    ])
    runner, sessao = await _montar(llm)
    final, _ = await conversar(runner, "u1", sessao.id, "Quero umas caixas de goiaba pra sexta")
    pedido = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["triar_pedido"][0]["pedido"]
    assert pedido["itens"][0]["quantidade"] is None
    assert "quantidade:goiaba" in pedido["informacoes_ausentes"]
    assert "comprador" in pedido["informacoes_ausentes"]
    assert "caixas" in final
