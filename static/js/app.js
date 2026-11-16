/* Sabor da Terra – chat da cooperativa
 *
 * CONTRATO ASSUMIDO DE POST /api/chat (ainda é esqueleto no backend; confirmar com
 * Murilo e David). Segundo docs/ESTRUTURA.md, models/chat_model.py terá usuário,
 * sessão, mensagem e agentes acionados. Os NOMES dos campos abaixo são suposição:
 *   Requisição : { "message": "texto", "session_id": "abc" | null, "user_id": "u-123" }
 *   Resposta   : { "reply": "texto", "session_id": "abc",
 *                  "agents": ["pedidos_agent"],
 *                  "sources": [ { "source": "laudo.pdf", "page": 3 } ],
 *                  "alerts":  [ { "type": "fora_de_safra", "message": "...", "severity": "high" } ] }
 *   Erro       : { "detail": "mensagem" }  (padrão do FastAPI) ou { "error": { "message": "..." } }
 *
 * O normalizador aceita nomes alternativos de campo (ex.: response, answer,
 * agentes, agentes_acionados, file, filename, pagina), então pequenas diferenças
 * no backend não quebram a tela. Se o contrato final for diferente, basta mexer em
 * CONFIG, em enviarMensagem() (corpo da requisição) e em normalizarResposta().
 */
(function (raiz) {
  "use strict";

  var CONFIG = {
    endpointChat: "/api/chat",
    endpointSaude: "/api/health",
    chaveSessao: "sabor_session_id",
    chaveUsuario: "sabor_user_id",
    tempoLimiteMs: 60000, // agentes com RAG podem demorar
    limiteCaracteres: 4000
  };

  /* ====================== lógica pura (testável) ====================== */

  function primeiroTexto() {
    for (var i = 0; i < arguments.length; i++) {
      var v = arguments[i];
      if (typeof v === "string" && v.trim() !== "") return v.trim();
    }
    return "";
  }

  function normalizarFonte(f) {
    if (typeof f === "string") return { arquivo: f, pagina: null };
    if (!f || typeof f !== "object") return null;
    var arquivo = primeiroTexto(f.source, f.file, f.filename, f.arquivo, f.document, f.documento, f.name, f.nome, f.title);
    if (!arquivo) return null;
    var pag = f.page != null ? f.page : (f.pagina != null ? f.pagina : (f.page_number != null ? f.page_number : null));
    return { arquivo: arquivo, pagina: pag === "" ? null : pag };
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
    var texto = primeiroTexto(dados.reply, dados.response, dados.answer, dados.message, dados.resposta, dados.text);
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

  /** Quebra texto do assistente em blocos simples: parágrafos, listas e **negrito**. */
  function parseTextoSimples(texto) {
    var linhas = String(texto).replace(/\r\n/g, "\n").split("\n");
    var blocos = [];
    var atual = null;
    function fechar() { if (atual) { blocos.push(atual); atual = null; } }
    linhas.forEach(function (linha) {
      var ul = /^\s*[-*•]\s+(.*)$/.exec(linha);
      var ol = /^\s*\d+[.)]\s+(.*)$/.exec(linha);
      if (ul) {
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
    });
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

  var logica = {
    CONFIG: CONFIG,
    normalizarResposta: normalizarResposta,
    normalizarFonte: normalizarFonte,
    normalizarAlerta: normalizarAlerta,
    rotuloAgente: rotuloAgente,
    extrairMensagemDeErro: extrairMensagemDeErro,
    descreverErro: descreverErro,
    parseTextoSimples: parseTextoSimples,
    partesNegrito: partesNegrito
  };

  if (typeof module !== "undefined" && module.exports) module.exports = logica;
  if (typeof document === "undefined") return; // ambiente de teste (Node): para aqui

  /* ====================== interface (navegador) ====================== */

  var el = {
    transcricao: document.getElementById("transcricao"),
    vazio: document.getElementById("vazio"),
    form: document.getElementById("formulario"),
    campo: document.getElementById("mensagem"),
    enviar: document.getElementById("enviar"),
    contador: document.getElementById("contador"),
    faixaErro: document.getElementById("faixa-erro"),
    faixaErroTexto: document.getElementById("faixa-erro-texto"),
    tentar: document.getElementById("tentar-novamente"),
    fecharErro: document.getElementById("fechar-erro"),
    novaConversa: document.getElementById("nova-conversa"),
    status: document.getElementById("status-servidor"),
    statusTexto: document.getElementById("status-texto")
  };

  var estado = { sessionId: null, enviando: false, ultimaMensagem: "", digitandoEl: null };

  /* ---- sessão ---- */
  function lerSessao() {
    try { return window.sessionStorage.getItem(CONFIG.chaveSessao); } catch (e) { return null; }
  }
  function gravarSessao(id) {
    try {
      if (id) window.sessionStorage.setItem(CONFIG.chaveSessao, id);
      else window.sessionStorage.removeItem(CONFIG.chaveSessao);
    } catch (e) { /* armazenamento indisponível: a sessão vive só em memória */ }
  }
  estado.sessionId = lerSessao();

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
  estado.userId = obterUsuario();

  /* ---- DOM helpers (sempre textContent: nada de innerHTML com texto do servidor) ---- */
  function criar(tag, classe, texto) {
    var n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto != null) n.textContent = texto;
    return n;
  }

  function preencherInline(pai, texto) {
    partesNegrito(texto).forEach(function (p) {
      pai.appendChild(p.negrito ? criar("strong", null, p.texto) : document.createTextNode(p.texto));
    });
  }

  function renderizarTexto(pai, texto) {
    parseTextoSimples(texto).forEach(function (b) {
      if (b.tipo === "p") {
        var p = criar("p");
        b.linhas.forEach(function (l, i) { if (i) p.appendChild(document.createElement("br")); preencherInline(p, l); });
        pai.appendChild(p);
      } else {
        var lista = criar(b.tipo);
        b.itens.forEach(function (it) { var li = criar("li"); preencherInline(li, it); lista.appendChild(li); });
        pai.appendChild(lista);
      }
    });
  }

  function rolarParaOFim() { el.transcricao.scrollTop = el.transcricao.scrollHeight; }

  function esconderVazio() { if (el.vazio && el.vazio.parentNode) el.vazio.parentNode.removeChild(el.vazio); }

  function adicionarMensagemUsuario(texto) {
    esconderVazio();
    var m = criar("article", "msg msg-usuario");
    m.appendChild(criar("span", "msg-autor", "Você"));
    m.appendChild(criar("div", "bolha", texto));
    el.transcricao.appendChild(m);
    rolarParaOFim();
  }

  function adicionarDigitando() {
    var m = criar("article", "msg msg-assistente");
    m.setAttribute("aria-label", "O assistente está respondendo");
    m.appendChild(criar("span", "msg-autor", "Assistente"));
    var b = criar("div", "bolha");
    var d = criar("span", "digitando");
    d.setAttribute("role", "status");
    d.setAttribute("aria-label", "Carregando resposta");
    d.appendChild(criar("span")); d.appendChild(criar("span")); d.appendChild(criar("span"));
    b.appendChild(d); m.appendChild(b);
    el.transcricao.appendChild(m);
    rolarParaOFim();
    return m;
  }

  function removerDigitando() {
    if (estado.digitandoEl && estado.digitandoEl.parentNode) estado.digitandoEl.parentNode.removeChild(estado.digitandoEl);
    estado.digitandoEl = null;
  }

  function adicionarMensagemAssistente(r) {
    var m = criar("article", "msg msg-assistente");
    m.appendChild(criar("span", "msg-autor", "Assistente"));

    if (r.alertas.length) {
      var ul = criar("ul", "alertas");
      ul.setAttribute("aria-label", "Alertas");
      r.alertas.forEach(function (a) {
        var li = criar("li", "alerta");
        li.setAttribute("data-nivel", a.nivel);
        li.appendChild(criar("span", "alerta-rotulo", a.rotulo + ":"));
        li.appendChild(criar("span", null, a.texto));
        ul.appendChild(li);
      });
      m.appendChild(ul);
    }

    if (r.texto) {
      var b = criar("div", "bolha");
      renderizarTexto(b, r.texto);
      m.appendChild(b);
    }

    if (r.fontes.length) {
      var bloco = criar("div", "fontes");
      bloco.appendChild(criar("p", "fontes-titulo", "Fontes"));
      var lista = criar("ul", "fontes-lista");
      r.fontes.forEach(function (f) {
        var li = criar("li", "fonte");
        li.appendChild(criar("span", null, f.arquivo));
        if (f.pagina != null) li.appendChild(criar("span", "fonte-pag", "p. " + f.pagina));
        lista.appendChild(li);
      });
      bloco.appendChild(lista);
      m.appendChild(bloco);
    }

    if (r.agentes.length) {
      var ag = criar("p", "agentes");
      ag.appendChild(criar("span", "agentes-titulo", "Agentes acionados: "));
      ag.appendChild(document.createTextNode(r.agentes.join(", ")));
      m.appendChild(ag);
    }

    el.transcricao.appendChild(m);
    rolarParaOFim();
  }

  /* ---- erro ---- */
  function mostrarErro(info) {
    el.faixaErroTexto.textContent = info.mensagem;
    el.tentar.hidden = !info.podeTentarDeNovo;
    el.faixaErro.hidden = false;
  }
  function limparErro() { el.faixaErro.hidden = true; el.faixaErroTexto.textContent = ""; }

  /* ---- estado do composer ---- */
  function definirEnviando(valor) {
    estado.enviando = valor;
    el.enviar.disabled = valor;
    el.campo.disabled = valor;
    el.enviar.textContent = valor ? "Enviando…" : "Enviar";
    el.transcricao.setAttribute("aria-busy", valor ? "true" : "false");
    if (!valor) el.campo.focus();
  }

  function ajustarAltura() {
    el.campo.style.height = "auto";
    el.campo.style.height = Math.min(el.campo.scrollHeight, 180) + "px";
    var n = el.campo.value.length;
    el.contador.textContent = n > CONFIG.limiteCaracteres * 0.8 ? n + "/" + CONFIG.limiteCaracteres : "";
  }

  /* ---- envio ---- */
  function lerCorpo(resp) {
    return resp.text().then(function (t) {
      if (!t) return null;
      try { return JSON.parse(t); } catch (e) { return { __texto: t }; }
    });
  }

  function enviarMensagem(texto, tentandoDeNovo) {
    if (estado.enviando) return;
    texto = texto.trim();
    if (!texto) return;

    limparErro();
    estado.ultimaMensagem = texto;
    if (!tentandoDeNovo) adicionarMensagemUsuario(texto);
    el.campo.value = "";
    ajustarAltura();
    definirEnviando(true);
    estado.digitandoEl = adicionarDigitando();

    var controle = new AbortController();
    var estourou = false;
    var timer = setTimeout(function () { estourou = true; controle.abort(); }, CONFIG.tempoLimiteMs);

    fetch(CONFIG.endpointChat, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({ message: texto, session_id: estado.sessionId, user_id: estado.userId }),
      signal: controle.signal
    })
      .then(function (resp) {
        return lerCorpo(resp).then(function (corpo) { return { resp: resp, corpo: corpo }; });
      })
      .then(function (r) {
        removerDigitando();
        if (!r.resp.ok) { mostrarErro(descreverErro("http", r.resp.status, r.corpo)); return; }
        if (!r.corpo || r.corpo.__texto !== undefined) { mostrarErro(descreverErro("formato")); return; }
        var dados = normalizarResposta(r.corpo);
        if (dados.sessionId && dados.sessionId !== estado.sessionId) {
          estado.sessionId = dados.sessionId;
          gravarSessao(dados.sessionId);
        }
        if (dados.vazia) { mostrarErro(descreverErro("vazia")); return; }
        adicionarMensagemAssistente(dados);
      })
      .catch(function (e) {
        removerDigitando();
        mostrarErro(descreverErro(estourou ? "tempo" : "rede"));
      })
      .then(function () {
        clearTimeout(timer);
        definirEnviando(false);
      });
  }

  /* ---- nova conversa ---- */
  function novaConversa() {
    if (estado.enviando) return;
    estado.sessionId = null;
    gravarSessao(null);
    limparErro();
    el.transcricao.textContent = "";
    var vazio = criar("div", "vazio");
    vazio.id = "vazio";
    vazio.appendChild(criar("h2", null, "Nova conversa iniciada"));
    vazio.appendChild(criar("p", null, "O assistente não lembra da conversa anterior. Escreva sua mensagem abaixo."));
    el.transcricao.appendChild(vazio);
    el.vazio = vazio;
    el.campo.value = "";
    ajustarAltura();
    el.campo.focus();
  }

  /* ---- saúde do servidor ---- */
  function verificarServidor() {
    var c = new AbortController();
    var t = setTimeout(function () { c.abort(); }, 5000);
    fetch(CONFIG.endpointSaude, { signal: c.signal })
      .then(function (r) { clearTimeout(t); definirStatus(r.ok); })
      .catch(function () { clearTimeout(t); definirStatus(false); });
  }
  function definirStatus(ok) {
    el.status.setAttribute("data-estado", ok ? "ok" : "erro");
    el.statusTexto.textContent = ok ? "Servidor conectado" : "Servidor indisponível";
  }

  /* ---- eventos ---- */
  el.form.addEventListener("submit", function (ev) { ev.preventDefault(); enviarMensagem(el.campo.value, false); });

  el.campo.addEventListener("keydown", function (ev) {
    if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
      ev.preventDefault();
      el.form.requestSubmit();
    }
  });
  el.campo.addEventListener("input", ajustarAltura);

  el.tentar.addEventListener("click", function () { enviarMensagem(estado.ultimaMensagem, true); });
  el.fecharErro.addEventListener("click", function () { limparErro(); el.campo.focus(); });
  el.novaConversa.addEventListener("click", novaConversa);

  Array.prototype.forEach.call(document.querySelectorAll(".atalho"), function (b) {
    b.addEventListener("click", function () {
      if (estado.enviando) return;
      el.campo.value = b.getAttribute("data-texto") || "";
      ajustarAltura();
      el.campo.focus();
    });
  });

  window.addEventListener("online", verificarServidor);
  window.addEventListener("offline", function () { definirStatus(false); });

  el.campo.disabled = false; // o esqueleto original deixava o campo desabilitado
  ajustarAltura();
  verificarServidor();
  el.campo.focus();
})(typeof window !== "undefined" ? window : this);
