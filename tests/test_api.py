from fastapi.testclient import TestClient
import pytest

from main import app

client = TestClient(app)


def test_health_retorna_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["storage_backend"] == "local"
    assert isinstance(body["ai_configured"], bool)


def test_health_nao_expoe_segredos():
    body = client.get("/api/health").json()
    assert "google_api_key" not in body


def test_pagina_inicial_e_servida():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sabor da Terra" in response.text


def test_arquivos_estaticos_sao_servidos():
    assert client.get("/css/style.css").status_code == 200
    assert client.get("/js/app.js").status_code == 200


def test_documentacao_automatica_disponivel():
    assert client.get("/docs").status_code == 200
    assert "/api/health" in client.get("/openapi.json").json()["paths"]


# ---------------------------------------------------------------------------
# POST /api/chat (Membro 5 — Interface/QA)
# Pulados enquanto a rota não existir (Fase 4). Quando ela for registrada em
# main.py, passam a rodar sozinhos. Os testes que chamam o modelo de IA só
# rodam com GOOGLE_API_KEY configurada (ai_configured = true em /api/health).
# ---------------------------------------------------------------------------

def _rota_chat_existe() -> bool:
    return "/api/chat" in client.get("/openapi.json").json()["paths"]


def _ia_configurada() -> bool:
    return bool(client.get("/api/health").json().get("ai_configured"))


precisa_da_rota = pytest.mark.skipif(not _rota_chat_existe(), reason="POST /api/chat ainda não implementada (Fase 4)")
precisa_da_ia = pytest.mark.skipif(
    not _rota_chat_existe() or not _ia_configurada(),
    reason="exige /api/chat implementada e GOOGLE_API_KEY configurada",
)


def _texto_da_resposta(corpo: dict) -> str:
    for nome in ("reply", "response", "answer", "resposta", "texto"):
        if isinstance(corpo.get(nome), str) and corpo[nome].strip():
            return corpo[nome]
    return ""


@precisa_da_rota
def test_chat_rejeita_corpo_vazio():
    assert client.post("/api/chat", json={}).status_code == 422


@precisa_da_rota
def test_chat_exige_message():
    assert client.post("/api/chat", json={"user_id": "u-teste", "session_id": None}).status_code == 422


@precisa_da_rota
def test_chat_rejeita_message_vazia():
    r = client.post("/api/chat", json={"user_id": "u-teste", "session_id": None, "message": ""})
    assert r.status_code in (400, 422)


@precisa_da_rota
def test_chat_erro_de_validacao_traz_detalhe():
    corpo = client.post("/api/chat", json={}).json()
    assert "detail" in corpo or "error" in corpo  # o frontend lê os dois formatos


@precisa_da_rota
def test_chat_documentado_no_openapi():
    op = client.get("/openapi.json").json()["paths"]["/api/chat"]
    assert "post" in op


@precisa_da_ia
def test_chat_devolve_texto_e_session_id():
    r = client.post("/api/chat", json={"user_id": "u-teste", "session_id": None,
                                       "message": "Quais produtores têm certificação orgânica vigente para mel?"})
    assert r.status_code == 200
    corpo = r.json()
    assert _texto_da_resposta(corpo)
    assert isinstance(corpo["session_id"], str) and corpo["session_id"]
    for campo in ("agents", "sources", "alerts"):
        if campo in corpo:
            assert isinstance(corpo[campo], list)


@precisa_da_ia
def test_chat_preserva_session_id_entre_mensagens():
    r1 = client.post("/api/chat", json={"user_id": "u-teste", "session_id": None, "message": "Olá"})
    sid = r1.json()["session_id"]
    r2 = client.post("/api/chat", json={"user_id": "u-teste", "session_id": sid, "message": "E sobre queijo?"})
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid
