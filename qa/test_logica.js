// Testes da lógica pura do frontend. Rodar: node qa/test_logica.js
const assert = require("assert");
const L = require("../static/js/app.js");

let ok = 0;
function t(nome, fn) {
  try { fn(); ok++; console.log("  ok  -", nome); }
  catch (e) { console.error("FALHOU -", nome, "\n   ", e.message); process.exitCode = 1; }
}

t("resposta completa é normalizada", () => {
  const r = L.normalizarResposta({
    reply: "Olá", session_id: "s1",
    sources: [{ source: "a.pdf", page: 3 }, { file: "b.docx" }],
    alerts: [{ type: "fora_de_safra", message: "Fora de safra", severity: "high" }],
  });
  assert.strictEqual(r.texto, "Olá");
  assert.strictEqual(r.sessionId, "s1");
  assert.deepStrictEqual(r.fontes, [{ arquivo: "a.pdf", pagina: 3, tipo: "PDF" }, { arquivo: "b.docx", pagina: null, tipo: "DOCX" }]);
  assert.strictEqual(r.alertas[0].nivel, "alto");
  assert.strictEqual(r.alertas[0].rotulo, "Fora de safra");
  assert.strictEqual(r.vazia, false);
});

t("nomes alternativos de campo (response/answer/pagina)", () => {
  assert.strictEqual(L.normalizarResposta({ response: "x" }).texto, "x");
  assert.strictEqual(L.normalizarResposta({ answer: "y" }).texto, "y");
  assert.deepStrictEqual(L.normalizarFonte({ arquivo: "c.pdf", pagina: 7, tipo: "PDF" }), { arquivo: "c.pdf", pagina: 7, tipo: "PDF" });
});

t("fonte como texto simples", () => {
  assert.deepStrictEqual(L.normalizarFonte("laudo.pdf"), { arquivo: "laudo.pdf", pagina: null, tipo: "PDF" });
});

t("resposta vazia é detectada", () => {
  assert.strictEqual(L.normalizarResposta({ reply: "   " }).vazia, true);
  assert.strictEqual(L.normalizarResposta(null).vazia, true);
  assert.strictEqual(L.normalizarResposta({}).vazia, true);
});

t("só alerta, sem texto, não é vazia", () => {
  const r = L.normalizarResposta({ alerts: [{ type: "sem_evidencia", message: "sem fonte" }] });
  assert.strictEqual(r.vazia, false);
});

t("fontes inválidas são descartadas", () => {
  const r = L.normalizarResposta({ reply: "x", sources: [null, 5, {}, { source: "ok.pdf" }] });
  assert.strictEqual(r.fontes.length, 1);
});

t("página 0 e texto vazio de página", () => {
  assert.strictEqual(L.normalizarFonte({ source: "a", page: 0 }).pagina, 0);
  assert.strictEqual(L.normalizarFonte({ source: "a", page: "" }).pagina, null);
});

t("erros: FastAPI 422, string, objeto error", () => {
  assert.strictEqual(L.extrairMensagemDeErro({ detail: "falhou" }), "falhou");
  assert.strictEqual(L.extrairMensagemDeErro({ detail: [{ msg: "a" }, { msg: "b" }] }), "a; b");
  assert.strictEqual(L.extrairMensagemDeErro({ error: { message: "m" } }), "m");
  assert.strictEqual(L.extrairMensagemDeErro(null), "");
});

t("descreverErro cobre rede, tempo, vazia, 404, 422, 429, 503, 500", () => {
  assert.ok(/conexão/i.test(L.descreverErro("rede").mensagem));
  assert.ok(/demorou/i.test(L.descreverErro("tempo").mensagem));
  assert.ok(/nenhuma resposta/i.test(L.descreverErro("vazia").mensagem));
  assert.ok(/\/api\/chat/.test(L.descreverErro("http", 404).mensagem));
  assert.strictEqual(L.descreverErro("http", 422, { detail: [{ msg: "curta" }] }).podeTentarDeNovo, false);
  assert.ok(/curta/.test(L.descreverErro("http", 422, { detail: [{ msg: "curta" }] }).mensagem));
  assert.strictEqual(L.descreverErro("http", 429).podeTentarDeNovo, true);
  assert.ok(/indisponível/i.test(L.descreverErro("http", 503).mensagem));
  assert.ok(/erro/i.test(L.descreverErro("http", 500, { detail: "boom" }).mensagem));
});

t("texto simples: parágrafo, listas e negrito", () => {
  const b = L.parseTextoSimples("Título\nlinha 2\n\n- a\n- b\n\n1. um\n2. dois");
  assert.deepStrictEqual(b.map(x => x.tipo), ["p", "ul", "ol"]);
  assert.deepStrictEqual(b[0].linhas, ["Título", "linha 2"]);
  assert.deepStrictEqual(b[1].itens, ["a", "b"]);
  assert.deepStrictEqual(L.partesNegrito("x **y** z"), [
    { negrito: false, texto: "x " }, { negrito: true, texto: "y" }, { negrito: false, texto: " z" }]);
});

t("HTML vindo do servidor não vira marcação (fica como texto)", () => {
  const b = L.parseTextoSimples("<img src=x onerror=alert(1)>");
  assert.strictEqual(b[0].linhas[0], "<img src=x onerror=alert(1)>"); // o app.js usa textContent
});

t("agentes acionados: rótulos, duplicados e root_agent oculto", () => {
  assert.strictEqual(L.rotuloAgente("pedidos_agent"), "Pedidos");
  assert.strictEqual(L.rotuloAgente("documentos_agent"), "Documentos");
  assert.strictEqual(L.rotuloAgente("root_agent"), "");
  assert.strictEqual(L.rotuloAgente({ name: "produtores_agent" }), "Produtores");
  const r = L.normalizarResposta({ reply: "x", agents: ["root_agent", "pedidos_agent", "pedidos_agent"] });
  assert.deepStrictEqual(r.agentes, ["Pedidos"]);
  assert.deepStrictEqual(L.normalizarResposta({ reply: "x", agentes_acionados: "documentos_agent" }).agentes, ["Documentos"]);
  assert.deepStrictEqual(L.normalizarResposta({ reply: "x" }).agentes, []);
});

t("501 (controller ainda esqueleto) tem mensagem própria e não oferece tentar de novo", () => {
  const e = L.descreverErro("http", 501);
  assert.ok(/ainda não foi implementada/i.test(e.mensagem));
  assert.strictEqual(e.podeTentarDeNovo, false);
});

t("tipoArquivo deduz a extensão", () => {
  assert.strictEqual(L.tipoArquivo("laudo.pdf"), "PDF");
  assert.strictEqual(L.tipoArquivo("contrato.docx"), "DOCX");
  assert.strictEqual(L.tipoArquivo("sem_extensao"), "DOC");
});

t("tabela markdown vira bloco table com alinhamento", () => {
  const b = L.parseTextoSimples("Resumo\n\n| Item | Qtd |\n|:--|--:|\n| Morango | 40 kg |\n| Queijo | 20 kg |\n\nFim");
  assert.deepStrictEqual(b.map(x => x.tipo), ["p", "table", "p"]);
  assert.deepStrictEqual(b[1].cab, ["Item", "Qtd"]);
  assert.deepStrictEqual(b[1].alinh, ["left", "right"]);
  assert.strictEqual(b[1].linhas.length, 2);
  assert.deepStrictEqual(b[1].linhas[0], ["Morango", "40 kg"]);
});

t("linha com barra sem separador não vira tabela", () => {
  const b = L.parseTextoSimples("a | b\nc | d");
  assert.strictEqual(b[0].tipo, "p");
});

t("títulos markdown", () => {
  const b = L.parseTextoSimples("## Itens\ntexto");
  assert.strictEqual(b[0].tipo, "h");
  assert.strictEqual(b[0].texto, "Itens");
});

t("inline: negrito, itálico, código e link http", () => {
  const p = L.partesInline("**a** *b* `c` [d](https://x.com/y) fim");
  assert.deepStrictEqual(p.map(x => x.tipo), ["negrito", "texto", "italico", "texto", "codigo", "texto", "link", "texto"]);
  assert.strictEqual(p[6].href, "https://x.com/y");
});

t("links javascript: não viram link", () => {
  const p = L.partesInline("[x](javascript:alert(1))");
  assert.ok(p.every(x => x.tipo !== "link"));
});

t("ehNumerico reconhece quantidades e valores", () => {
  ["40 kg", "R$ 4.280,00", "12%", "7"].forEach(v => assert.ok(L.ehNumerico(v), v));
  ["Morango", "sexta"].forEach(v => assert.ok(!L.ehNumerico(v), v));
});

t("formatarHora devolve HH:MM", () => {
  assert.ok(/^\d{2}:\d{2}$/.test(L.formatarHora(Date.now())));
  assert.strictEqual(L.formatarHora("lixo"), "");
});

t("aceita o campo 'texto' do ChatResponse do backend", () => {
  const r = L.normalizarResposta({ texto: "Olá", session_id: "s1", agents: ["pedidos_agent"] });
  assert.strictEqual(r.texto, "Olá");
  assert.strictEqual(r.sessionId, "s1");
  assert.deepStrictEqual(r.agentes, ["Pedidos"]);
});

console.log(`\n${ok} testes passaram` + (process.exitCode ? " (há falhas)" : ""));
