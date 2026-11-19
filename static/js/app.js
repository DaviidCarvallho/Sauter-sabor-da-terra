/* Sabor da Terra – chat da cooperativa
 *
 * Etapa 3 (original): checkHealth() consulta /api/health e mostra a versão do servidor.
 * Etapa 7 (esta): chat conectado a POST /api/chat.
 *
 * CONTRATO DE POST /api/chat (implementado em models/chat_model.py e api/chat_controller.py):
 *   Requisição : { "message": "texto", "session_id": "abc" | null, "user_id": "u-123" }
 *   Resposta   : { "answer": "texto", "session_id": "abc", "status": "success",
 *                  "agents_used": ["pedidos_agent"],
 *                  "sources": [ { "source": "contratos/x.txt", "page": null } ],
 *                  "alerts": [ { "tipo": "fora_de_safra", "severidade": "alta", "mensagem": "...", "produto": "morango" } ] }
 *   "alerts" vem do código (triagem determinística), só na triagem de pedidos; vazio nas demais respostas.
 *   Erros      : { "detail": "mensagem" } com 422 (corpo inválido), 429 (limite da IA),
 *                503 (IA não configurada) e 502 (falha do assistente).
 *
 * O normalizador aceita nomes alternativos de campo (ex.: response, answer,
 * agentes, agentes_acionados, file, filename, pagina), então pequenas diferenças
 * no backend não quebram a tela. Se o contrato final for diferente, basta mexer em
 * CONFIG, no corpo da requisição (sendMessage) e em normalizarResposta().
 *
 * O texto do assistente aceita Markdown simples (títulos, listas, tabelas, negrito,
 * itálico, código e links http/https). Tudo entra na página por textContent.
 */
(function (root) {
  "use strict";

  var CONFIG = {
    endpointChat: "/api/chat",
    endpointSaude: "/api/health",
    chaveSessao: "sabor_session_id",
    chaveUsuario: "sabor_user_id",
    chaveHistorico: "sabor_historico",
    maxMensagensGuardadas: 60,
    tempoLimiteMs: 60000, // agentes com RAG podem demorar
    avisoLentoMs: 10000,
    limiteCaracteres: 4000,
    enviarUserId: true // ponha false se o schema Pydantic do backend não aceitar user_id
  };

  /* ====================== lógica pura (testável em Node) ====================== */

  function primeiroTexto() {
    for (var i = 0; i < arguments.length; i++) {
      var v = arguments[i];
      if (typeof v === "string" && v.trim() !== "") return v.trim();
    }
    return "";
  }

  /** "laudo.pdf" -> "PDF"; sem extensão conhecida -> "DOC". */
  function tipoArquivo(nome) {
    var m = /\.([a-z0-9]{2,5})$/i.exec(String(nome || ""));
    return m ? m[1].toUpperCase() : "DOC";
  }

  function normalizarFonte(f) {
    if (typeof f === "string") return { arquivo: f, pagina: null, tipo: tipoArquivo(f) };
    if (!f || typeof f !== "object") return null;
    var arquivo = primeiroTexto(f.source, f.file, f.filename, f.arquivo, f.document, f.documento, f.name, f.nome, f.title);
    if (!arquivo) return null;
    var pag = f.page != null ? f.page : (f.pagina != null ? f.pagina : (f.page_number != null ? f.page_number : null));
    return { arquivo: arquivo, pagina: pag === "" ? null : pag, tipo: tipoArquivo(arquivo) };
  }

  var ROTULOS = {
    fora_de_safra: "Fora de safra",
    sem_evidencia: "Sem evidência",
    quantidade_acima_capacidade: "Quantidade acima da capacidade",
    pendencia_financeira: "Pendência financeira",
    certificacao_vencida: "Certificação vencida"
  };

  function rotuloDoTipo(tipo) {
    if (!tipo) return "Atenção";
    if (ROTULOS[tipo]) return ROTULOS[tipo];
    var t = tipo.replace(/[_-]+/g, " ").trim();
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function normalizarAlerta(a) {
    if (typeof a === "string") return { rotulo: "Atenção", texto: a, nivel: "medio" };
    if (!a || typeof a !== "object") return null;
    var texto = primeiroTexto(a.message, a.mensagem, a.text, a.texto, a.description, a.descricao);
    var tipo = primeiroTexto(a.type, a.tipo, a.code, a.codigo);
    if (!texto && !tipo) return null;
    var sev = String(a.severity || a.severidade || a.level || a.nivel || "").toLowerCase();
    var nivel = "medio";
    if (/high|alta|alto|critical|critic|error|erro/.test(sev)) nivel = "alto";
    else if (/info|low|baixa|baixo/.test(sev)) nivel = "info";
    return { rotulo: rotuloDoTipo(tipo), texto: texto || rotuloDoTipo(tipo), nivel: nivel };
  }

  /** "pedidos_agent" -> "Pedidos"; o orquestrador (root_agent) não precisa aparecer. */
  function rotuloAgente(a) {
    var nome = typeof a === "string" ? a : (a && typeof a === "object" ? primeiroTexto(a.name, a.nome, a.agent, a.agente, a.id) : "");
    if (!nome) return "";
    var t = nome.replace(/_?agent$/i, "").replace(/[_-]+/g, " ").trim();
    if (!t || /^root$/i.test(t)) return "";
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function normalizarAgentes(dados) {
    var lista = dados.agents || dados.agentes || dados.agents_used || dados.agentes_acionados || dados.agentesAcionados;
    if (typeof lista === "string") lista = [lista];
    if (!Array.isArray(lista)) return [];
    var vistos = {};
    return lista.map(rotuloAgente).filter(function (x) {
      if (!x || vistos[x]) return false;
      vistos[x] = true;
      return true;
    });
  }

  function normalizarResposta(dados) {
    if (!dados || typeof dados !== "object") return { vazia: true, texto: "", fontes: [], alertas: [], agentes: [], sessionId: null };
    var texto = primeiroTexto(dados.reply, dados.response, dados.answer, dados.message, dados.resposta, dados.texto, dados.text);
    var fontes = (Array.isArray(dados.sources) ? dados.sources : (Array.isArray(dados.fontes) ? dados.fontes : []))
      .map(normalizarFonte).filter(Boolean);
    var alertas = (Array.isArray(dados.alerts) ? dados.alerts : (Array.isArray(dados.alertas) ? dados.alertas : []))
      .map(normalizarAlerta).filter(Boolean);
    var sid = primeiroTexto(dados.session_id, dados.sessionId, dados.sessao_id);
    return { vazia: texto === "" && alertas.length === 0, texto: texto, fontes: fontes, alertas: alertas, agentes: normalizarAgentes(dados), sessionId: sid || null };
  }

  function extrairMensagemDeErro(corpo) {
    if (!corpo) return "";
    if (typeof corpo === "string") return corpo;
    var d = corpo.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) { // 422 do FastAPI
      return d.map(function (x) { return x && x.msg ? x.msg : ""; }).filter(Boolean).join("; ");
    }
    if (corpo.error) return typeof corpo.error === "string" ? corpo.error : primeiroTexto(corpo.error.message, corpo.error.mensagem);
    return primeiroTexto(corpo.message, corpo.mensagem);
  }

  /** Converte qualquer falha em { mensagem, podeTentarDeNovo }. */
  function descreverErro(tipo, status, corpo) {
    var doServidor = extrairMensagemDeErro(corpo);
    if (tipo === "tempo") return { mensagem: "O assistente demorou demais para responder. Tente de novo em instantes.", podeTentarDeNovo: true };
    if (tipo === "rede") return { mensagem: "Sem conexão com o servidor. Confira sua internet e se o servidor está ligado.", podeTentarDeNovo: true };
    if (tipo === "vazia") return { mensagem: "O assistente não devolveu nenhuma resposta. Tente reformular a pergunta.", podeTentarDeNovo: true };
    if (tipo === "formato") return { mensagem: "A resposta do servidor veio em um formato inesperado. Avise a equipe de desenvolvimento.", podeTentarDeNovo: false };
    if (status === 422 || status === 400) return { mensagem: doServidor ? "Mensagem não aceita: " + doServidor : "O servidor não aceitou essa mensagem. Revise o texto e tente de novo.", podeTentarDeNovo: false };
    if (status === 501) return { mensagem: "Essa função ainda não foi implementada no servidor (o chat do backend está em construção).", podeTentarDeNovo: false };
    if (status === 404) return { mensagem: "O servidor não encontrou a rota do chat (/api/chat). Ela pode ainda não estar implementada.", podeTentarDeNovo: false };
    if (status === 429) return { mensagem: "Muitas mensagens em pouco tempo. Aguarde um momento e tente de novo.", podeTentarDeNovo: true };
    if (status === 502 || status === 503 || status === 504) return { mensagem: "O servidor está indisponível no momento. Tente de novo em alguns instantes.", podeTentarDeNovo: true };
    if (status >= 500) return { mensagem: "O servidor encontrou um erro" + (doServidor ? ": " + doServidor.replace(/[.\s]+$/, "") : "") + ". Tente de novo.", podeTentarDeNovo: true };
    return { mensagem: doServidor || "Não foi possível concluir o envio.", podeTentarDeNovo: true };
  }

  /* ---- Markdown simples ---- */

  function ehSeparadorTabela(l) {
    return l.indexOf("|") >= 0 && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l);
  }

  function celulasDaLinha(l) {
    var t = l.trim().replace(/^\|/, "").replace(/\|$/, "");
    return t.split("|").map(function (c) { return c.trim(); });
  }

  /** Valores como "40 kg", "R$ 4.280,00", "12%", "7": alinhados à direita nas tabelas. */
  function ehNumerico(txt) {
    return /^[-+]?\s*(R\$\s*)?\d[\d.,\s]*(\s*(kg|g|l|ml|un|cx|caixas?|%))?$/i.test(String(txt).trim());
  }

  /** Quebra o texto do assistente em blocos: p, h, ul, ol, table. */
  function parseTextoSimples(texto) {
    var linhas = String(texto).replace(/\r\n/g, "\n").split("\n");
    var blocos = [];
    var atual = null;
    var i = 0;
    function fechar() { if (atual) { blocos.push(atual); atual = null; } }

    while (i < linhas.length) {
      var linha = linhas[i];

      if (linha.indexOf("|") >= 0 && i + 1 < linhas.length && ehSeparadorTabela(linhas[i + 1])) {
        fechar();
        var cab = celulasDaLinha(linha);
        var alinh = celulasDaLinha(linhas[i + 1]).map(function (c) {
          var e = /^:/.test(c), d = /:$/.test(c);
          return e && d ? "center" : d ? "right" : e ? "left" : "";
        });
        var corpo = [];
        i += 2;
        while (i < linhas.length && linhas[i].trim() !== "" && linhas[i].indexOf("|") >= 0) {
          corpo.push(celulasDaLinha(linhas[i]));
          i++;
        }
        blocos.push({ tipo: "table", cab: cab, alinh: alinh, linhas: corpo });
        continue;
      }

      var h = /^\s{0,3}(#{1,4})\s+(.*?)\s*#*\s*$/.exec(linha);
      var ul = /^\s*[-*•]\s+(.*)$/.exec(linha);
      var ol = /^\s*\d+[.)]\s+(.*)$/.exec(linha);
      if (h) {
        fechar();
        blocos.push({ tipo: "h", nivel: Math.min(h[1].length + 2, 5), texto: h[2] });
      } else if (ul) {
        if (!atual || atual.tipo !== "ul") { fechar(); atual = { tipo: "ul", itens: [] }; }
        atual.itens.push(ul[1]);
      } else if (ol) {
        if (!atual || atual.tipo !== "ol") { fechar(); atual = { tipo: "ol", itens: [] }; }
        atual.itens.push(ol[1]);
      } else if (linha.trim() === "") {
        fechar();
      } else {
        if (!atual || atual.tipo !== "p") { fechar(); atual = { tipo: "p", linhas: [] }; }
        atual.linhas.push(linha);
      }
      i++;
    }
    fechar();
    return blocos;
  }

  function partesNegrito(texto) {
    var partes = [];
    var re = /\*\*([^*]+)\*\*/g;
    var ultimo = 0, m;
    while ((m = re.exec(texto)) !== null) {
      if (m.index > ultimo) partes.push({ negrito: false, texto: texto.slice(ultimo, m.index) });
      partes.push({ negrito: true, texto: m[1] });
      ultimo = m.index + m[0].length;
    }
    if (ultimo < texto.length) partes.push({ negrito: false, texto: texto.slice(ultimo) });
    return partes;
  }

  /** Negrito, itálico, `código` e [texto](https://...). Só links http/https viram link. */
  function partesInline(texto) {
    var partes = [];
    var re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\)|\*[^*\s][^*]*\*)/g;
    var ultimo = 0, m;
    while ((m = re.exec(texto)) !== null) {
      if (m.index > ultimo) partes.push({ tipo: "texto", texto: texto.slice(ultimo, m.index) });
      var t = m[0];
      if (t.indexOf("**") === 0) partes.push({ tipo: "negrito", texto: t.slice(2, -2) });
      else if (t.charAt(0) === "`") partes.push({ tipo: "codigo", texto: t.slice(1, -1) });
      else if (t.charAt(0) === "[") {
        var mm = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(t);
        partes.push({ tipo: "link", texto: mm[1], href: mm[2] });
      } else partes.push({ tipo: "italico", texto: t.slice(1, -1) });
      ultimo = m.index + t.length;
    }
    if (ultimo < texto.length) partes.push({ tipo: "texto", texto: texto.slice(ultimo) });
    return partes;
  }

  function formatarHora(ts) {
    var d = new Date(ts);
    if (isNaN(d.getTime())) return "";
    function p(n) { return (n < 10 ? "0" : "") + n; }
    return p(d.getHours()) + ":" + p(d.getMinutes());
  }

  var logica = {
    CONFIG: CONFIG,
    normalizarResposta: normalizarResposta,
    normalizarFonte: normalizarFonte,
    normalizarAlerta: normalizarAlerta,
    rotuloAgente: rotuloAgente,
    tipoArquivo: tipoArquivo,
    extrairMensagemDeErro: extrairMensagemDeErro,
    descreverErro: descreverErro,
    parseTextoSimples: parseTextoSimples,
    partesNegrito: partesNegrito,
    partesInline: partesInline,
    ehNumerico: ehNumerico,
    formatarHora: formatarHora
  };

  if (typeof module !== "undefined" && module.exports) module.exports = logica;
  if (typeof document === "undefined") return; // ambiente de teste (Node): para aqui

  /* ====================== interface (navegador) ====================== */

  var statusEl = document.getElementById("status");
  var statusText = document.getElementById("status-text");
  var messagesEl = document.getElementById("messages");
  var composerEl = document.getElementById("composer");
  var inputEl = document.getElementById("input");
  var sendEl = document.getElementById("send");
  var cancelEl = document.getElementById("cancel");
  var countEl = document.getElementById("count");
  var jumpEl = document.getElementById("jump");
  var noticeEl = document.getElementById("notice");
  var noticeText = document.getElementById("notice-text");
  var retryEl = document.getElementById("retry");
  var dismissEl = document.getElementById("dismiss");
  var newChatEl = document.getElementById("new-chat");
  var welcomeEl = document.getElementById("welcome");
  var welcomeModelo = welcomeEl ? welcomeEl.cloneNode(true) : null;

  var estado = {
    sessionId: null, userId: null, enviando: false, ultimaMensagem: "",
    digitandoEl: null, controle: null, cancelado: false, timerLento: null, historico: []
  };

  /* ---- estado do servidor (mantido da etapa 3) ---- */
  async function checkHealth() {
    try {
      var response = await fetch(CONFIG.endpointSaude);
      if (!response.ok) throw new Error("HTTP " + response.status);
      var data = await response.json();
      statusEl.dataset.state = "ok";
      statusText.textContent = data && data.version ? "Servidor online · v" + data.version : "Servidor online";
    } catch (error) {
      statusEl.dataset.state = "error";
      statusText.textContent = "Servidor indisponível";
      console.error("Falha ao consultar /api/health:", error);
    }
  }

  /* ---- armazenamento (sempre com try/catch: pode estar bloqueado) ---- */
  function lerSessao() { try { return window.sessionStorage.getItem(CONFIG.chaveSessao); } catch (e) { return null; } }
  function gravarSessao(id) {
    try {
      if (id) window.sessionStorage.setItem(CONFIG.chaveSessao, id);
      else window.sessionStorage.removeItem(CONFIG.chaveSessao);
    } catch (e) { /* a sessão vive só em memória */ }
  }
  function lerHistorico() {
    try {
      var h = JSON.parse(window.sessionStorage.getItem(CONFIG.chaveHistorico) || "[]");
      return Array.isArray(h) ? h : [];
    } catch (e) { return []; }
  }
  function gravarHistorico() {
    try {
      var h = estado.historico.slice(-CONFIG.maxMensagensGuardadas);
      window.sessionStorage.setItem(CONFIG.chaveHistorico, JSON.stringify(h));
    } catch (e) { /* sem espaço ou bloqueado: a conversa só não sobrevive ao recarregar */ }
  }
  function limparHistorico() {
    estado.historico = [];
    try { window.sessionStorage.removeItem(CONFIG.chaveHistorico); } catch (e) { /* ignora */ }
  }
  /* Sem login no protótipo: cada navegador recebe um id anônimo estável (o backend mantém sessão por usuário). */
  function obterUsuario() {
    var id = null;
    try { id = window.localStorage.getItem(CONFIG.chaveUsuario); } catch (e) { id = null; }
    if (id) return id;
    id = (window.crypto && window.crypto.randomUUID)
      ? "u-" + window.crypto.randomUUID()
      : "u-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
    try { window.localStorage.setItem(CONFIG.chaveUsuario, id); } catch (e) { /* vale só nesta página */ }
    return id;
  }
  estado.sessionId = lerSessao();
  estado.userId = obterUsuario();

  /* ---- DOM helpers (sempre textContent: nada de HTML vindo do servidor) ---- */
  var SVG_NS = "http://www.w3.org/2000/svg";
  var ICONES = {
    alerta: ["M12 4l9 16H3z", "M12 10v4", "M12 17.2v.01"],
    info: ["M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z", "M12 11v5", "M12 8v.01"],
    copiar: ["M11 9h6a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2h-6a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2z", "M5 15V7a2 2 0 0 1 2-2h8"],
    ok: ["M5 12.5l4.5 4.5L19 7"]
  };

  function icone(nome) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    ICONES[nome].forEach(function (d) {
      var p = document.createElementNS(SVG_NS, "path");
      p.setAttribute("d", d);
      svg.appendChild(p);
    });
    return svg;
  }

  function criar(tag, classe, texto) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto != null) n.textContent = texto;
    return n;
  }

  function preencherInline(pai, texto) {
    partesInline(texto).forEach(function (p) {
      if (p.tipo === "negrito") pai.appendChild(criar("strong", null, p.texto));
      else if (p.tipo === "italico") pai.appendChild(criar("em", null, p.texto));
      else if (p.tipo === "codigo") pai.appendChild(criar("code", null, p.texto));
      else if (p.tipo === "link") {
        var a = criar("a", null, p.texto);
        a.href = p.href;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        pai.appendChild(a);
      } else pai.appendChild(document.createTextNode(p.texto));
    });
  }

  function renderizarTexto(pai, texto) {
    parseTextoSimples(texto).forEach(function (b) {
      if (b.tipo === "p") {
        var p = criar("p");
        b.linhas.forEach(function (l, i) { if (i) p.appendChild(document.createElement("br")); preencherInline(p, l); });
        pai.appendChild(p);
      } else if (b.tipo === "h") {
        var h = criar("h" + b.nivel);
        preencherInline(h, b.texto);
        pai.appendChild(h);
      } else if (b.tipo === "table") {
        pai.appendChild(montarTabela(b));
      } else {
        var lista = criar(b.tipo);
        b.itens.forEach(function (it) { var li = criar("li"); preencherInline(li, it); lista.appendChild(li); });
        pai.appendChild(lista);
      }
    });
  }

  function classeDaCelula(b, idx, valor) {
    var a = b.alinh[idx] || (valor && ehNumerico(valor) ? "right" : "");
    return a ? "is-" + a : "";
  }

  function montarTabela(b) {
    var wrap = criar("div", "table-wrap");
    var t = criar("table");
    var thead = criar("thead");
    var trh = criar("tr");
    b.cab.forEach(function (c, i) {
      var th = criar("th", b.alinh[i] ? "is-" + b.alinh[i] : "");
      th.scope = "col";
      preencherInline(th, c);
      trh.appendChild(th);
    });
    thead.appendChild(trh);
    t.appendChild(thead);
    var tbody = criar("tbody");
    b.linhas.forEach(function (linha) {
      var tr = criar("tr");
      b.cab.forEach(function (_, i) {
        var td = criar("td", classeDaCelula(b, i, linha[i] || ""));
        preencherInline(td, linha[i] || "");
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    t.appendChild(tbody);
    wrap.appendChild(t);
    return wrap;
  }

  /* ---- rolagem inteligente ---- */
  function pertoDoFim() { return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 96; }
  function rolarParaOFim() { messagesEl.scrollTop = messagesEl.scrollHeight; jumpEl.hidden = true; }
  function aposAdicionar(deveRolar) { if (deveRolar) rolarParaOFim(); else jumpEl.hidden = false; }

  function removerBoasVindas() {
    var w = document.getElementById("welcome");
    if (w && w.parentNode) w.parentNode.removeChild(w);
  }

  function criarAvatar() { return criar("div", "avatar", "ST"); }

  /* ---- mensagens ---- */
  function addUserMessage(texto, ts) {
    removerBoasVindas();
    var noFim = pertoDoFim();
    var li = criar("li", "message message--user");
    li.appendChild(criar("div", "message__body", texto));
    li.appendChild(criar("span", "message__time", formatarHora(ts)));
    messagesEl.appendChild(li);
    aposAdicionar(true || noFim);
  }

  function copiarTexto(texto) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(texto);
    return new Promise(function (resolve, reject) {
      try {
        var t = document.createElement("textarea");
        t.value = texto;
        t.setAttribute("readonly", "");
        t.style.position = "fixed";
        t.style.opacity = "0";
        document.body.appendChild(t);
        t.select();
        var ok = document.execCommand("copy");
        document.body.removeChild(t);
        if (ok) resolve(); else reject(new Error("copy"));
      } catch (e) { reject(e); }
    });
  }

  function botaoCopiar(texto) {
    var b = criar("button", "icon-button");
    b.type = "button";
    var rotulo = criar("span", null, "Copiar");
    rotulo.setAttribute("role", "status");
    b.appendChild(icone("copiar"));
    b.appendChild(rotulo);
    b.addEventListener("click", function () {
      copiarTexto(texto).then(function () {
        rotulo.textContent = "Copiado";
      }, function () {
        rotulo.textContent = "Não foi possível copiar";
      }).then(function () {
        setTimeout(function () { rotulo.textContent = "Copiar"; }, 1800);
      });
    });
    return b;
  }

  function addAssistantMessage(r, ts) {
    var noFim = pertoDoFim();
    var li = criar("li", "message message--assistant");
    li.appendChild(criarAvatar());
    var main = criar("div", "message__main");

    var cab = criar("div", "message__head");
    cab.appendChild(criar("span", "message__author", "Assistente"));
    cab.appendChild(criar("span", "message__time", formatarHora(ts)));
    if (r.texto) cab.appendChild(botaoCopiar(r.texto));
    main.appendChild(cab);

    if (r.alertas.length) {
      var ul = criar("ul", "alerts");
      ul.setAttribute("aria-label", "Alertas");
      r.alertas.forEach(function (a) {
        var classe = "alert" + (a.nivel === "alto" ? " alert--high" : a.nivel === "info" ? " alert--info" : "");
        var item = criar("li", classe);
        item.appendChild(icone(a.nivel === "info" ? "info" : "alerta"));
        var txt = criar("div");
        txt.appendChild(criar("span", "alert__label", a.rotulo + ":"));
        txt.appendChild(document.createTextNode(a.texto));
        item.appendChild(txt);
        ul.appendChild(item);
      });
      main.appendChild(ul);
    }

    if (r.texto) {
      var corpo = criar("div", "message__body");
      renderizarTexto(corpo, r.texto);
      main.appendChild(corpo);
    }

    if (r.fontes.length) {
      var bloco = criar("div", "sources");
      bloco.appendChild(criar("p", "sources__title", "Fontes consultadas"));
      var lista = criar("ul", "sources__list");
      r.fontes.forEach(function (f) {
        var item = criar("li", "source");
        item.appendChild(criar("span", "source__type", f.tipo || tipoArquivo(f.arquivo)));
        item.appendChild(criar("span", "source__name", f.arquivo));
        if (f.pagina != null) item.appendChild(criar("span", "source__page", "p. " + f.pagina));
        lista.appendChild(item);
      });
      bloco.appendChild(lista);
      main.appendChild(bloco);
    }

    if (r.agentes.length) {
      var ag = criar("p", "agents");
      ag.appendChild(criar("span", "agents__title", "Agentes acionados: "));
      ag.appendChild(document.createTextNode(r.agentes.join(", ")));
      main.appendChild(ag);
    }

    li.appendChild(main);
    messagesEl.appendChild(li);
    aposAdicionar(noFim);
  }

  function addSystemMessage(texto) {
    var li = criar("li", "message message--system", texto);
    messagesEl.appendChild(li);
    rolarParaOFim();
  }

  function addTyping() {
    var li = criar("li", "message message--assistant");
    li.appendChild(criarAvatar());
    var t = criar("div", "typing");
    t.setAttribute("role", "status");
    var pontos = criar("span", "typing__dots");
    pontos.setAttribute("aria-hidden", "true");
    pontos.appendChild(criar("span")); pontos.appendChild(criar("span")); pontos.appendChild(criar("span"));
    var txt = criar("span", "typing__text", "Consultando a cooperativa…");
    t.appendChild(pontos);
    t.appendChild(txt);
    li.appendChild(t);
    messagesEl.appendChild(li);
    rolarParaOFim();
    estado.timerLento = setTimeout(function () {
      txt.textContent = "Ainda consultando. Isso pode levar alguns segundos.";
    }, CONFIG.avisoLentoMs);
    return li;
  }

  function removeTyping() {
    clearTimeout(estado.timerLento);
    if (estado.digitandoEl && estado.digitandoEl.parentNode) estado.digitandoEl.parentNode.removeChild(estado.digitandoEl);
    estado.digitandoEl = null;
  }

  /* ---- erro ---- */
  function showNotice(info) {
    noticeText.textContent = info.mensagem;
    retryEl.hidden = !info.podeTentarDeNovo;
    noticeEl.hidden = false;
  }
  function clearNotice() { noticeEl.hidden = true; noticeText.textContent = ""; }

  /* ---- campo de mensagem ---- */
  function setSending(valor) {
    estado.enviando = valor;
    sendEl.disabled = valor;
    cancelEl.hidden = !valor;
    messagesEl.setAttribute("aria-busy", valor ? "true" : "false");
    if (!valor) inputEl.focus();
  }

  function ajustarAltura() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 144) + "px";
    var n = inputEl.value.length;
    countEl.textContent = n > CONFIG.limiteCaracteres * 0.8 ? n + " de " + CONFIG.limiteCaracteres : "";
  }

  /* ---- envio ---- */
  function lerCorpo(resp) {
    return resp.text().then(function (t) {
      if (!t) return null;
      try { return JSON.parse(t); } catch (e) { return { __texto: t }; }
    });
  }

  function montarCorpo(texto) {
    var corpo = { message: texto, session_id: estado.sessionId };
    if (CONFIG.enviarUserId) corpo.user_id = estado.userId;
    return corpo;
  }

  function sendMessage(texto, tentandoDeNovo) {
    if (estado.enviando) return;
    texto = texto.trim();
    if (!texto) return;

    clearNotice();
    estado.ultimaMensagem = texto;
    estado.cancelado = false;
    if (!tentandoDeNovo) {
      var agora = Date.now();
      addUserMessage(texto, agora);
      estado.historico.push({ papel: "user", texto: texto, ts: agora });
      gravarHistorico();
    }
    inputEl.value = "";
    ajustarAltura();
    setSending(true);
    estado.digitandoEl = addTyping();

    var controle = new AbortController();
    estado.controle = controle;
    var estourou = false;
    var timer = setTimeout(function () { estourou = true; controle.abort(); }, CONFIG.tempoLimiteMs);

    fetch(CONFIG.endpointChat, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(montarCorpo(texto)),
      signal: controle.signal
    })
      .then(function (resp) {
        return lerCorpo(resp).then(function (corpo) { return { resp: resp, corpo: corpo }; });
      })
      .then(function (r) {
        removeTyping();
        if (!r.resp.ok) { showNotice(descreverErro("http", r.resp.status, r.corpo)); return; }
        if (!r.corpo || r.corpo.__texto !== undefined) { showNotice(descreverErro("formato")); return; }
        var dados = normalizarResposta(r.corpo);
        if (dados.sessionId && dados.sessionId !== estado.sessionId) {
          estado.sessionId = dados.sessionId;
          gravarSessao(dados.sessionId);
        }
        if (dados.vazia) { showNotice(descreverErro("vazia")); return; }
        var ts = Date.now();
        addAssistantMessage(dados, ts);
        estado.historico.push({ papel: "assistant", texto: dados.texto, alertas: dados.alertas, fontes: dados.fontes, agentes: dados.agentes, ts: ts });
        gravarHistorico();
      })
      .catch(function () {
        removeTyping();
        if (estado.cancelado) {
          addSystemMessage("Resposta cancelada.");
          if (!inputEl.value) { inputEl.value = texto; ajustarAltura(); }
          return;
        }
        showNotice(descreverErro(estourou ? "tempo" : "rede"));
      })
      .then(function () {
        clearTimeout(timer);
        estado.controle = null;
        setSending(false);
      });
  }

  function cancelarEnvio() {
    if (!estado.enviando || !estado.controle) return;
    estado.cancelado = true;
    estado.controle.abort();
  }

  /* ---- nova conversa e histórico ---- */
  function renderizarHistorico() {
    if (!estado.historico.length) return;
    removerBoasVindas();
    estado.historico.forEach(function (m) {
      if (m.papel === "user") addUserMessage(String(m.texto || ""), m.ts);
      else addAssistantMessage({
        texto: String(m.texto || ""),
        alertas: Array.isArray(m.alertas) ? m.alertas : [],
        fontes: Array.isArray(m.fontes) ? m.fontes : [],
        agentes: Array.isArray(m.agentes) ? m.agentes : []
      }, m.ts);
    });
    rolarParaOFim();
  }

  function newChat() {
    if (estado.enviando) cancelarEnvio();
    estado.sessionId = null;
    gravarSessao(null);
    limparHistorico();
    clearNotice();
    messagesEl.textContent = "";
    if (welcomeModelo) messagesEl.appendChild(welcomeModelo.cloneNode(true));
    jumpEl.hidden = true;
    inputEl.value = "";
    ajustarAltura();
    inputEl.focus();
  }

  /* ---- eventos ---- */
  composerEl.addEventListener("submit", function (ev) { ev.preventDefault(); sendMessage(inputEl.value, false); });

  inputEl.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      if (!estado.enviando) composerEl.requestSubmit();
    }
  });
  inputEl.addEventListener("input", ajustarAltura);

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && estado.enviando) cancelarEnvio();
  });

  messagesEl.addEventListener("click", function (ev) { // sugestões (sobrevivem a "Nova conversa")
    var b = ev.target.closest ? ev.target.closest(".suggestion") : null;
    if (!b) return;
    inputEl.value = b.getAttribute("data-text") || "";
    ajustarAltura();
    inputEl.focus();
  });
  messagesEl.addEventListener("scroll", function () { if (pertoDoFim()) jumpEl.hidden = true; });
  jumpEl.addEventListener("click", function () { rolarParaOFim(); inputEl.focus(); });

  retryEl.addEventListener("click", function () { sendMessage(estado.ultimaMensagem, true); });
  dismissEl.addEventListener("click", function () { clearNotice(); inputEl.focus(); });
  cancelEl.addEventListener("click", cancelarEnvio);
  newChatEl.addEventListener("click", newChat);

  window.addEventListener("online", checkHealth);
  window.addEventListener("offline", function () {
    statusEl.dataset.state = "error";
    statusText.textContent = "Servidor indisponível";
  });

  inputEl.disabled = false; // na etapa 3 o campo ficava desabilitado
  sendEl.disabled = false;
  estado.historico = lerHistorico();
  renderizarHistorico();
  ajustarAltura();
  checkHealth();
  inputEl.focus();
})(typeof window !== "undefined" ? window : this);
