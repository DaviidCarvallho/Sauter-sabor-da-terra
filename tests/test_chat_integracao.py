"""Fluxo ponta a ponta sem custo: API -> chat_service -> root_agent -> pedidos_agent -> tool ->
serviços -> repositórios -> resposta. Só o LLM é simulado."""

import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import services.chat_service as chat_mod
from agents.agent import construir_root_agent
from main import app
from services.chat_service import ChatService, get_chat_service
from tests.llm_simulado import ScriptedLlm, chamar, respostas_de_ferramenta_na_requisicao, texto

MSG = "Bom dia, o Mercado Bom Preço precisa de 100 kg de tomate para sexta-feira."
ITENS = [{"produto": "tomate", "quantidade": 100, "unidade": "kg"}]


def _servico(respostas):
    llm = ScriptedLlm(respostas=respostas)
    return llm, ChatService(agente=construir_root_agent(llm))


def _cliente(servico):
    app.dependency_overrides[get_chat_service] = lambda: servico
    return TestClient(app)


@pytest.fixture(autouse=True)
def _limpa_overrides():
    yield
    app.dependency_overrides.clear()


def _roteiro_pedido():
    return [
        chamar("pedidos_agent", request=MSG),
        chamar("triar_pedido", itens=ITENS, comprador="Mercado Bom Preço", prazo="sexta-feira",
               tipo="pedido_firme", data_referencia="2026-10-28"),
        texto("Tomate 100 kg, entrega sexta 30/10, urgência urgente."),
        texto("Triagem concluída: tomate 100 kg para 30/10 (urgente)."),
    ]


def test_fluxo_completo_de_pedido():
    llm, servico = _servico(_roteiro_pedido())
    r = _cliente(servico).post("/api/chat", json={"user_id": "u1", "session_id": None, "message": MSG})

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["answer"].startswith("Triagem concluída")
    assert corpo["agents_used"] == ["pedidos_agent"]
    assert corpo["status"] == "success" and corpo["sources"] == []
    assert isinstance(corpo["session_id"], str) and corpo["session_id"]
    # A ferramenta real consultou serviços e repositórios (dados da cooperativa), não o LLM.
    triagem = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["triar_pedido"][0]
    assert triagem["status"] == "sucesso"
    assert triagem["pedido"]["itens"][0]["produtores_elegiveis"]


def test_session_id_e_preservado_e_contexto_continua():
    llm, servico = _servico([texto("a"), texto("b")])
    c = _cliente(servico)
    sid = c.post("/api/chat", json={"user_id": "u1", "message": "Primeira"}).json()["session_id"]
    r2 = c.post("/api/chat", json={"user_id": "u1", "session_id": sid, "message": "Segunda"})
    assert r2.json()["session_id"] == sid
    assert "Primeira" in str(llm.requisicoes[1].contents)


def test_session_id_desconhecido_ou_de_outro_usuario_gera_sessao_nova():
    llm, servico = _servico([texto("a"), texto("b"), texto("c")])
    c = _cliente(servico)
    sid = c.post("/api/chat", json={"user_id": "u1", "message": "segredo de u1"}).json()["session_id"]
    outra = c.post("/api/chat", json={"user_id": "u2", "session_id": sid, "message": "oi"}).json()
    assert outra["session_id"] != sid
    assert "segredo de u1" not in str(llm.requisicoes[1].contents)
    desconhecida = c.post("/api/chat", json={"user_id": "u1", "session_id": "nao-existe", "message": "oi"})
    assert desconhecida.status_code == 200 and desconhecida.json()["session_id"] != "nao-existe"


def test_campo_user_e_aceito_como_alias_de_user_id():
    _, servico = _servico([texto("ok")])
    r = _cliente(servico).post("/api/chat", json={"user": "u9", "message": "oi"})
    assert r.status_code == 200


@pytest.mark.parametrize("corpo", [{}, {"user_id": "u"}, {"message": ""}, {"message": "   "},
                                   {"message": "x" * 4001}])
def test_corpo_invalido_retorna_422(corpo):
    _, servico = _servico([])
    r = _cliente(servico).post("/api/chat", json=corpo)
    assert r.status_code == 422 and "detail" in r.json()


def test_ia_nao_configurada_retorna_503_sem_detalhes(monkeypatch):
    monkeypatch.setattr(chat_mod, "get_settings", lambda: SimpleNamespace(google_api_key=None))
    r = _cliente(ChatService()).post("/api/chat", json={"message": "oi"})
    assert r.status_code == 503
    assert "GOOGLE_API_KEY" not in r.text


def test_falha_do_modelo_retorna_502_sem_vazar_detalhes():
    _, servico = _servico([])  # roteiro vazio: o "modelo" falha na primeira chamada
    r = _cliente(servico).post("/api/chat", json={"message": "oi"})
    assert r.status_code == 502
    assert "roteiro" not in r.text.lower() and "Assertion" not in r.text


def test_resposta_vazia_retorna_502():
    _, servico = _servico([texto("   ")])
    assert _cliente(servico).post("/api/chat", json={"message": "oi"}).status_code == 502


def test_logs_nao_contem_o_texto_da_mensagem(caplog):
    _, servico = _servico([texto("ok")])
    with caplog.at_level(logging.DEBUG):
        _cliente(servico).post("/api/chat", json={"message": "CPF 123.456.789-09 conta 0437"})
    assert "123.456.789-09" not in caplog.text and "0437" not in caplog.text


def test_chat_documentado_no_openapi():
    assert "post" in TestClient(app).get("/openapi.json").json()["paths"]["/api/chat"]


class _LlmChaveInvalida(ScriptedLlm):
    async def generate_content_async(self, llm_request, stream=False):
        from google.genai import errors

        raise errors.ClientError(
            400, {"error": {"code": 400, "message": "API key not valid.", "status": "INVALID_ARGUMENT",
                            "details": [{"reason": "API_KEY_INVALID"}]}})
        yield  # pragma: no cover


def test_chave_de_ia_invalida_retorna_503_e_nao_502():
    servico = ChatService(agente=construir_root_agent(_LlmChaveInvalida()))
    r = _cliente(servico).post("/api/chat", json={"message": "oi"})
    assert r.status_code == 503
    assert "API key" not in r.text and "API_KEY" not in r.text
