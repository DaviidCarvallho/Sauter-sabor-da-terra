from fastapi.testclient import TestClient

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
