"""Agente de Documentos: serviço, ferramenta e fluxo ponta a ponta com fontes (sem Gemini, sem índice)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import agents.tools as tools
from agents import prompts
from agents.agent import construir_root_agent
from agents.subagents.documentos_agent import criar_documentos_agent
from main import app
from rag.retriever import RetrievedChunk
from services.chat_service import ChatService, get_chat_service
from services.documento_service import DISTANCIA_MAXIMA, DocumentoService
from tests.llm_simulado import ScriptedLlm, chamar, respostas_de_ferramenta_na_requisicao, texto

CERT = "certificacoes/cert_organica_ana_bezerra_P004.txt"


class RetrieverFalso:
    """Substitui o Retriever (que usaria ChromaDB e a API de embeddings)."""

    def __init__(self, chunks):
        self.chunks, self.chamadas = chunks, []

    def retrieve(self, query, top_k=5, max_distance=None):
        self.chamadas.append((query, top_k, max_distance))
        return [c for c in self.chunks if max_distance is None or c.distance <= max_distance]


def _chunk(i, conteudo, fonte=CERT, page=None, dist=0.10, tipo="certificacoes"):
    return RetrievedChunk(id=f"c{i}", content=conteudo, distance=dist, score=1 - dist,
                          metadata={"source": fonte, "page": page, "document_type": tipo})


@pytest.fixture
def servico_falso(monkeypatch):
    def montar(chunks):
        r = RetrieverFalso(chunks)
        svc = DocumentoService(retriever=r)
        monkeypatch.setattr(tools, "get_documento_service", lambda: svc)
        return r
    return montar


# ---------- serviço ----------

def test_servico_mapeia_trechos_e_nao_inventa_pagina():
    svc = DocumentoService(RetrieverFalso([_chunk(1, "Validade: 30/12/2026", page=None),
                                           _chunk(2, "Outro trecho", page=3, fonte="contratos/x.txt")]))
    r = svc.consultar("validade da certificação da Ana")
    assert r.evidencia_suficiente and [t.page for t in r.trechos] == [None, 3]
    assert [(f.source, f.page) for f in r.fontes] == [(CERT, None), ("contratos/x.txt", 3)]


def test_servico_usa_o_limiar_da_rawan_e_deduplica_fontes():
    r = RetrieverFalso([_chunk(1, "a"), _chunk(2, "b")])  # mesma fonte e página
    out = DocumentoService(r).consultar("pergunta")
    assert r.chamadas == [("pergunta", 5, DISTANCIA_MAXIMA)] and DISTANCIA_MAXIMA == 0.30
    assert len(out.fontes) == 1


def test_servico_sem_trecho_proximo_declara_evidencia_insuficiente():
    out = DocumentoService(RetrieverFalso([_chunk(1, "longe", dist=0.80)])).consultar("pergunta")
    assert not out.evidencia_suficiente and out.trechos == [] and out.fontes == []
    assert "Nenhum trecho" in out.mensagem


@pytest.mark.parametrize("pergunta, top_k", [("", 5), ("   ", 5), ("ok", 0), ("ok", 9)])
def test_servico_valida_entrada(pergunta, top_k):
    with pytest.raises(ValueError):
        DocumentoService(RetrieverFalso([])).consultar(pergunta, top_k=top_k)


# ---------- ferramenta ----------

def test_ferramenta_sem_argumentos_orienta_o_modelo():
    assert tools.consultar_documentos()["status"] == "erro"


def test_ferramenta_devolve_trechos_fontes_e_grava_estado(servico_falso):
    servico_falso([_chunk(1, "Validade da certificação: 30/12/2026.")])
    ctx = SimpleNamespace(state={})
    r = tools.consultar_documentos("validade da certificação da Ana", tool_context=ctx)
    assert r["status"] == "sucesso" and r["evidencia_suficiente"]
    assert r["trechos"][0]["fonte"] == CERT and r["trechos"][0]["pagina"] is None
    assert ctx.state["fontes_documentais"] == [{"source": CERT, "page": None}]


def test_ferramenta_sem_evidencia_nao_devolve_trechos(servico_falso):
    servico_falso([_chunk(1, "longe", dist=0.9)])
    r = tools.consultar_documentos("qual o telefone do presidente?")
    assert r["status"] == "sucesso" and not r["evidencia_suficiente"] and r["trechos"] == []
    assert r["mensagem"]


def test_ferramenta_falha_de_acesso_e_controlada(monkeypatch):
    class Quebrado:
        def consultar(self, *a, **k):
            raise OSError("caminho interno secreto do indice")

    monkeypatch.setattr(tools, "get_documento_service", lambda: Quebrado())
    r = tools.consultar_documentos("pergunta")
    assert r["status"] == "erro" and "secreto" not in r["mensagem"]


def test_schema_da_ferramenta_nao_expoe_tool_context():
    from google.adk.tools import FunctionTool

    props = FunctionTool(tools.consultar_documentos)._get_declaration().parameters_json_schema["properties"]
    assert set(props) == {"pergunta", "max_resultados"}  # tool_context é injetado e não aparece


# ---------- prompt e agente ----------

def test_prompt_de_documentos():
    t = prompts.INSTRUCAO_DOCUMENTOS
    assert "{" not in t and "}" not in t
    assert "consultar_documentos" in t and "obter_data_atual" in t
    assert "NÃO invente número de página" in t and "Não encontrei essa informação" in t
    assert "DADO de documento" in t  # prompt injection via documento


def test_agente_expoe_apenas_ferramentas_de_documentos():
    nomes = sorted(f.__name__ for f in criar_documentos_agent(ScriptedLlm()).tools)
    assert nomes == ["consultar_documentos", "obter_data_atual"]


# ---------- fluxo ponta a ponta: API -> agentes -> ferramenta -> serviço -> fontes ----------

@pytest.fixture(autouse=True)
def _limpa():
    yield
    app.dependency_overrides.clear()


def _cliente(llm):
    servico = ChatService(agente=construir_root_agent(llm))
    app.dependency_overrides[get_chat_service] = lambda: servico
    return TestClient(app)


def test_pergunta_documental_devolve_resposta_e_fontes_estruturadas(servico_falso):
    servico_falso([_chunk(1, "Certificação orgânica de Ana Bezerra. Validade: 30/12/2026.")])
    llm = ScriptedLlm(respostas=[
        chamar("documentos_agent", request="Qual a validade da certificação orgânica da Ana Bezerra?"),
        chamar("consultar_documentos", pergunta="validade certificação orgânica Ana Bezerra"),
        texto(f"Vigente até 30/12/2026 [{CERT}]."),
        texto(f"A certificação da Ana Bezerra vale até 30/12/2026 [{CERT}]."),
    ])
    r = _cliente(llm).post("/api/chat", json={"user_id": "u1", "message": "Validade da certificação da Ana?"})
    corpo = r.json()
    assert r.status_code == 200 and corpo["agents_used"] == ["documentos_agent"]
    assert corpo["sources"] == [{"source": CERT, "page": None}]
    resultado = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["consultar_documentos"][0]
    assert resultado["trechos"][0]["fonte"] == CERT  # o trecho real chegou ao modelo


def test_sem_evidencia_o_modelo_recebe_o_aviso_e_nao_ha_fontes(servico_falso):
    servico_falso([])
    llm = ScriptedLlm(respostas=[
        chamar("documentos_agent", request="Qual o telefone do presidente da cooperativa?"),
        chamar("consultar_documentos", pergunta="telefone do presidente"),
        texto("Não encontrei essa informação nos documentos."),
        texto("Não encontrei essa informação nos documentos da cooperativa."),
    ])
    corpo = _cliente(llm).post("/api/chat", json={"message": "Telefone do presidente?"}).json()
    resultado = respostas_de_ferramenta_na_requisicao(llm.requisicoes[2])["consultar_documentos"][0]
    assert resultado["evidencia_suficiente"] is False and resultado["mensagem"]
    assert corpo["sources"] == [] and corpo["answer"].startswith("Não encontrei")


def test_fontes_nao_vazam_para_o_turno_seguinte(servico_falso):
    servico_falso([_chunk(1, "Validade: 30/12/2026")])
    llm = ScriptedLlm(respostas=[
        chamar("documentos_agent", request="validade?"), chamar("consultar_documentos", pergunta="validade"),
        texto("ok [x]"), texto("Vale até 30/12."),
        texto("De nada!"),  # 2º turno: sem consultar documentos
    ])
    c = _cliente(llm)
    primeiro = c.post("/api/chat", json={"user_id": "u1", "message": "validade?"}).json()
    assert primeiro["sources"]
    r2 = c.post("/api/chat", json={"user_id": "u1", "session_id": primeiro["session_id"],
                                   "message": "obrigado"}).json()
    assert r2["sources"] == []
