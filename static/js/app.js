// Etapa 3: apenas verifica se o backend responde. O chat entra na etapa dos agentes.
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    statusEl.dataset.state = "ok";
    statusText.textContent = `Servidor online · v${data.version}`;
  } catch (error) {
    statusEl.dataset.state = "error";
    statusText.textContent = "Servidor indisponível";
    console.error("Falha ao consultar /api/health:", error);
  }
}

checkHealth();
