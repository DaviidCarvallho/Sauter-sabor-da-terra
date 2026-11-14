"""Verificações estáticas do frontend (não precisam de servidor, nem de FastAPI).

Rodar na raiz do projeto: pytest tests/test_frontend_estatico.py
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def ler(rel: str) -> str:
    return (STATIC / rel).read_text(encoding="utf-8")


def test_arquivos_existem():
    for rel in ("index.html", "css/style.css", "js/app.js"):
        assert (STATIC / rel).is_file(), f"static/{rel} não encontrado"


def test_idioma_e_viewport():
    html = ler("index.html")
    assert '<html lang="pt-BR">' in html
    assert 'name="viewport"' in html


def test_campo_de_mensagem_habilitado_e_com_rotulo():
    html = ler("index.html")
    campo = re.search(r"<textarea[^>]*>", html)
    assert campo, "textarea de mensagem não encontrada"
    assert "disabled" not in campo.group(0), "o campo de mensagem deve estar habilitado"
    assert 'for="mensagem"' in html, "o campo precisa de <label> associado"


def test_regiao_de_mensagens_e_acessivel():
    html = ler("index.html")
    assert 'role="log"' in html and 'aria-live="polite"' in html
    assert 'role="alert"' in html, "faixa de erro deve ser anunciada por leitores de tela"


def test_js_usa_fetch_para_api_chat_e_envia_session_id():
    js = ler("js/app.js")
    assert "fetch(" in js
    assert "/api/chat" in js
    assert "session_id" in js


def test_js_trata_tempo_limite_e_falha_de_rede():
    js = ler("js/app.js")
    assert "AbortController" in js
    assert "tempoLimiteMs" in js


def test_js_nao_injeta_html_do_servidor():
    js = ler("js/app.js")
    assert not re.search(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML", js), (
        "texto do servidor deve entrar por textContent (evita XSS)"
    )


def test_css_respeita_movimento_reduzido_e_foco_visivel():
    css = ler("css/style.css")
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css
