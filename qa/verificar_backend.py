"""Verifica o backend real (ou o simulado) contra o contrato do chat e os 4 cenários de aceitação.

Uso (com o servidor ligado):
    python qa/verificar_backend.py                       # http://127.0.0.1:8000 (FastAPI real)
    python qa/verificar_backend.py http://127.0.0.1:8001 # servidor simulado
Só usa a biblioteca padrão. Gera docs/evidencias/resultado_verificacao.md
"""
import json, sys, urllib.request, urllib.error, datetime, pathlib

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
SAIDA = pathlib.Path(__file__).resolve().parent.parent / "docs" / "evidencias" / "resultado_verificacao.md"
linhas, falhas = [], 0


def chamar(metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(BASE + caminho, data=dados, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except Exception:
            return e.code, None
    except Exception as e:
        return 0, str(e)


def texto(d, *nomes):
    for n in nomes:
        if isinstance(d, dict) and isinstance(d.get(n), str) and d[n].strip():
            return d[n]
    return ""


def checar(nome, ok, detalhe=""):
    global falhas
    falhas += 0 if ok else 1
    linhas.append(f"| {'OK' if ok else 'FALHOU'} | {nome} | {detalhe} |")
    print(("  ok    " if ok else "  FALHOU ") + nome + (f"  [{detalhe}]" if detalhe else ""))


def chat(msg, sid=None):
    return chamar("POST", "/api/chat", {"message": msg, "session_id": sid, "user_id": "u-qa-verificacao"})


print(f"Verificando {BASE}\n")
st, d = chamar("GET", "/api/health")
checar("GET /api/health responde 200", st == 200, f"status {st}")
if st == 0:
    print("\nServidor inacessível. Suba o backend (uvicorn main:app --reload) e tente de novo.")
    sys.exit(2)

st, d = chat("Preciso de 40 kg de morango e 20 kg de queijo coalho para sexta, pedido do Restaurante Brasa.")
if st in (404, 501):
    checar("POST /api/chat implementado", False, f"status {st}: o chat do backend ainda é esqueleto")
    print("\nO backend ainda não implementa o chat (fases 4 a 6). Rode de novo quando estiver pronto.")
else:
    reply = texto(d, "reply", "response", "answer", "resposta")
    sid = texto(d, "session_id", "sessionId")
    checar("A. Triagem: status 200 e texto de resposta", st == 200 and bool(reply), f"status {st}")
    checar("A. Triagem: devolve session_id", bool(sid))
    alertas = (d or {}).get("alerts") or (d or {}).get("alertas") or []
    checar("A. Triagem: campo de alertas é lista", isinstance(alertas, list), f"{len(alertas)} alerta(s)")
    st2, d2 = chat("Quais produtores têm certificação orgânica vigente para mel?", sid)
    checar("B. Documental: status 200 e texto", st2 == 200 and bool(texto(d2, "reply", "response", "answer", "resposta")), f"status {st2}")
    fontes = (d2 or {}).get("sources") or (d2 or {}).get("fontes") or []
    checar("B. Documental: traz fontes (arquivo e página)", len(fontes) > 0, f"{len(fontes)} fonte(s)")
    checar("B. Mantém a mesma sessão", texto(d2, "session_id", "sessionId") in ("", sid), "session_id preservado")
    st3, d3 = chat("Qual é o prazo de validade do contrato com a empresa Zebra Quântica Ltda?", sid)
    r3 = texto(d3, "reply", "response", "answer", "resposta")
    checar("C. Sem evidência: responde 200 sem inventar", st3 == 200 and bool(r3), r3[:70])
    st4, d4 = chat("Gere o resumo do mês do produtor Antônio Silva, com vendas e pendências.", sid)
    checar("D. Relatório de produtor: status 200 e texto", st4 == 200 and bool(texto(d4, "reply", "response", "answer", "resposta")), f"status {st4}")
    st5, d5 = chamar("POST", "/api/chat", {"message": ""})
    checar("Erro: mensagem vazia é rejeitada (4xx) com detalhe", 400 <= st5 < 500, f"status {st5}")
    print("\nOs cenários C e D exigem leitura humana: abra a interface e confira o texto e os alertas.")

SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(
    f"# Resultado da verificação\n\nServidor: `{BASE}` · {datetime.datetime.now():%d/%m/%Y %H:%M}\n\n"
    "| Resultado | Verificação | Detalhe |\n|---|---|---|\n" + "\n".join(linhas) + f"\n\n**Falhas: {falhas}**\n", encoding="utf-8")
print(f"\nRelatório salvo em {SAIDA}")
sys.exit(1 if falhas else 0)
