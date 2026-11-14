"""Servidor simulado para testar o frontend SEM o backend real.

Uso (a partir da pasta sabor-frontend):
    python qa/mock_server.py            # http://127.0.0.1:8001

Serve static/ e implementa /api/health e POST /api/chat com respostas fixas.
Palavras-chave na mensagem disparam cenários de falha para o QA:
    "erro500"  -> HTTP 500        "indisponivel" -> HTTP 503
    "invalido" -> HTTP 422        "vazio"        -> 200 sem texto
    "lento"    -> demora 70 s (estoura o tempo limite de 60 s)
    "formato"  -> 200 com corpo que não é JSON
    "naoimplementado" -> HTTP 501 (como um controller ainda esqueleto)
Usa só a biblioteca padrão; não precisa instalar nada.
"""
import json
import mimetypes
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
SESSOES = {}


def responder_chat(msg: str, sid: str):
    m = msg.lower()
    if "morango" in m or "pedido" in m or "kg" in m:
        return {
            "reply": "Pedido interpretado:\n- **Comprador:** Restaurante Brasa\n- **Itens:** morango 40 kg; queijo coalho 20 kg\n- **Prazo:** sexta-feira (urgência média)\n\nSugiro alocar o morango com 2 produtores para fechar a quantidade.",
            "session_id": sid,
            "agents": ["root_agent", "pedidos_agent"],
            "sources": [],
            "alerts": [
                {"type": "fora_de_safra", "message": "Morango está fora de safra neste mês; confirme disponibilidade.", "severity": "high"},
                {"type": "quantidade_acima_capacidade", "message": "40 kg excede a capacidade de um único produtor.", "severity": "medium"},
            ],
        }
    if "orgânica" in m or "organica" in m or "certifica" in m:
        return {
            "reply": "Dois produtores têm certificação orgânica vigente para mel:\n1. **Maria das Dores** (válida até 03/2027)\n2. **José Ferreira** (válida até 08/2027)",
            "session_id": sid,
            "agents": ["documentos_agent"],
            "sources": [
                {"source": "certificacao_organica_maria.pdf", "page": 2},
                {"source": "certificacao_organica_jose.docx"},
            ],
            "alerts": [],
        }
    if "contrato" in m or "distribuidora" in m:
        return {
            "reply": "Não encontrei essa informação nos documentos disponíveis. Não há contrato com distribuidora de Recife na base.",
            "session_id": sid,
            "agents": ["documentos_agent"],
            "sources": [],
            "alerts": [{"type": "sem_evidencia", "message": "Resposta sem fonte documental.", "severity": "info"}],
        }
    if "resumo" in m or "produtor" in m:
        return {
            "reply": "Resumo de **Antônio Silva** no mês:\n- Vendas: R$ 4.280,00\n- Pedidos alocados: 7\n- Pendências: 1 repasse em aberto\n\nRascunho de notificação: \"Olá, Antônio! Seu repasse de outubro está em análise.\"",
            "session_id": sid,
            "agents": ["produtores_agent"],
            "sources": [],
            "alerts": [{"type": "pendencia_financeira", "message": "Há 1 repasse em aberto.", "severity": "medium"}],
        }
    return {"reply": "Posso ajudar com pedidos, documentos e produtores. O que você precisa?", "session_id": sid, "sources": [], "alerts": []}


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, corpo):
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path == "/api/health":
            return self._json(200, {"status": "ok"})
        caminho = self.path.split("?")[0]
        if caminho == "/":
            caminho = "/index.html"
        arq = os.path.normpath(os.path.join(RAIZ, caminho.lstrip("/")))
        if not arq.startswith(os.path.normpath(RAIZ)) or not os.path.isfile(arq):
            return self._json(404, {"detail": "Not Found"})
        tipo = mimetypes.guess_type(arq)[0] or "application/octet-stream"
        with open(arq, "rb") as f:
            dados = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo + ("; charset=utf-8" if tipo.startswith("text/") or tipo.endswith("javascript") else ""))
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        if self.path != "/api/chat":
            return self._json(404, {"detail": "Not Found"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            corpo = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json(422, {"detail": [{"msg": "JSON inválido"}]})
        msg = (corpo.get("message") or "").strip()
        if not msg:
            return self._json(422, {"detail": [{"msg": "Campo 'message' é obrigatório"}]})
        m = msg.lower()
        if "erro500" in m:
            return self._json(500, {"detail": "Falha interna simulada"})
        if "indisponivel" in m:
            return self._json(503, {"detail": "Servico indisponivel"})
        if "naoimplementado" in m:
            return self._json(501, {"detail": "Not Implemented"})
        if "invalido" in m:
            return self._json(422, {"detail": [{"msg": "mensagem muito curta"}]})
        if "vazio" in m:
            return self._json(200, {"reply": "", "session_id": corpo.get("session_id") or str(uuid.uuid4()), "sources": [], "alerts": []})
        if "formato" in m:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"isto nao e json")
            return
        if "lento" in m:
            time.sleep(70)
        sid = corpo.get("session_id") or str(uuid.uuid4())
        SESSOES.setdefault(sid, []).append(msg)
        print("[mock] user_id =", corpo.get("user_id"), "| session_id =", sid)
        resp = responder_chat(msg, sid)
        resp["reply"] += "" if len(SESSOES[sid]) < 2 else f"\n\n(mensagem {len(SESSOES[sid])} desta sessão)"
        self._json(200, resp)

    def log_message(self, fmt, *args):  # log curto
        print("[mock]", self.command, self.path, "->", args[1] if len(args) > 1 else "")


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", 8001), Handler)
    print("Mock em http://127.0.0.1:8001  (Ctrl+C para parar)")
    srv.serve_forever()
