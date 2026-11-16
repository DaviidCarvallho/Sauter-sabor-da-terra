"""PROPOSTA de testes do contrato de POST /api/chat para somar a tests/test_api.py.

ATENÇÃO: não foi executado (o backend real não estava acessível quando foi escrito).
Os campos seguem o contrato assumido pelo frontend; ajuste se Murilo e David definirem outro.
Se a rota ainda não existir, os testes são pulados em vez de falhar.
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _rota_existe() -> bool:
    return any(getattr(r, "path", None) == "/api/chat" for r in app.routes)


pytestmark = pytest.mark.skipif(not _rota_existe(), reason="POST /api/chat ainda não implementada")


def test_chat_exige_message():
    r = client.post("/api/chat", json={"session_id": None})
    assert r.status_code == 422


def test_chat_devolve_campos_do_contrato():
    r = client.post("/api/chat", json={"message": "Quais produtores têm mel orgânico?", "session_id": None})
    assert r.status_code == 200
    corpo = r.json()
    assert isinstance(corpo["reply"], str) and corpo["reply"].strip()
    assert isinstance(corpo["session_id"], str) and corpo["session_id"]
    assert isinstance(corpo.get("sources", []), list)
    assert isinstance(corpo.get("alerts", []), list)


def test_chat_preserva_session_id():
    r1 = client.post("/api/chat", json={"message": "Olá", "session_id": None})
    sid = r1.json()["session_id"]
    r2 = client.post("/api/chat", json={"message": "E sobre queijo?", "session_id": sid})
    assert r2.json()["session_id"] == sid


def test_chat_mensagem_vazia_e_rejeitada():
    r = client.post("/api/chat", json={"message": "   ", "session_id": None})
    assert r.status_code in (400, 422)
