"""Verificações estáticas do frontend (não precisam de servidor, nem de FastAPI).

Rodar na raiz do projeto: pytest tests/test_frontend_estatico.py
"""
import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def ler(rel: str) -> str:
    return (STATIC / rel).read_text(encoding="utf-8")


def test_estrutura_de_arquivos():
    for rel in ("index.html", "css/style.css", "js/app.js"):
        assert (STATIC / rel).is_file(), f"static/{rel} não encontrado"


def test_html_mantem_identidade_e_ids_originais():
    html = ler("index.html")
    assert '<html lang="pt-BR">' in html
    assert "<title>Sabor da Terra</title>" in html
    assert 'name="viewport"' in html
    for ident in ("status", "status-text", "messages", "composer", "input"):
        assert f'id="{ident}"' in html, f"id original ausente: {ident}"
    assert 'href="/css/style.css"' in html and 'src="/js/app.js"' in html


def test_css_mantem_tokens_de_marca():
    css = ler("css/style.css")
    assert "--guava: #c4405f" in css and "--leaf: #2d6a3e" in css


def test_campo_de_mensagem_habilitado_e_com_rotulo():
    html = ler("index.html")
    campo = re.search(r"<textarea[^>]*>", html)
    assert campo, "campo de mensagem não encontrado"
    assert "disabled" not in campo.group(0), "o campo de mensagem deve estar habilitado"
    assert 'for="input"' in html, "o campo precisa de <label> associado"


def test_regioes_acessiveis():
    html = ler("index.html")
    assert 'aria-live="polite"' in html
    assert 'role="alert"' in html, "faixa de erro deve ser anunciada por leitores de tela"


def test_js_mantem_health_com_versao_e_usa_chat():
    js = ler("js/app.js")
    assert "/api/health" in js and "data.version" in js
    assert "fetch(" in js and "/api/chat" in js and "session_id" in js


def test_js_trata_tempo_limite():
    js = ler("js/app.js")
    assert "AbortController" in js and "tempoLimiteMs" in js


def test_js_nao_injeta_html_do_servidor():
    js = ler("js/app.js")
    assert not re.search(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML", js), (
        "texto do servidor deve entrar por textContent (evita XSS)"
    )


def test_css_respeita_movimento_reduzido_e_foco_visivel():
    css = ler("css/style.css")
    assert "prefers-reduced-motion" in css
    assert ":focus-visible" in css


def test_css_tem_tema_escuro_e_layout_movel():
    css = (STATIC / "css" / "style.css").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in css
    assert "max-width" in css and "40rem" in css


def test_html_tem_cancelar_copiar_e_ir_para_o_fim():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for ident in ("cancel", "jump", "new-chat", "retry", "notice"):
        assert f'id="{ident}"' in html


def test_js_preserva_session_id_e_historico():
    js = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
    assert "session_id" in js and "sessionStorage" in js
    assert "chaveHistorico" in js
