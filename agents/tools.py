"""Ferramentas dos agentes.

Função:
    Funções Python tipadas e com docstring que o ADK expõe ao modelo.

Responsabilidades:
    - Organizadas por especialista (hoje: pedidos; documentos e produtores entram nos módulos
      de Rawan e Arthur, seguindo o mesmo padrão)
    - Cada ferramenta é fina: valida a entrada, chama um serviço e devolve um dicionário simples
      com campo "status" ("sucesso" ou "erro")

Não deve:
    - Ler arquivos, CSV ou ChromaDB diretamente
    - Conter regra de negócio (safra, capacidade, preço e urgência vivem em services/)

Relações:
    Usa:        services.triagem_service, services.pedido_service, models.pedido_model
    Usado por:  agents.subagents.pedidos_agent

Observações:
    A docstring de cada ferramenta é o que o modelo lê para decidir quando usá-la.
    Erros esperados (entrada inválida, dado inexistente) viram {"status": "erro"}; falhas
    inesperadas propagam para o mecanismo de retentativa e telemetria do ADK 2.x.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from models.pedido_model import ItemPedidoEntrada
from services.pedido_service import NOMES_DIAS_PT, PedidoService
from services.triagem_service import TriagemService, resolver_prazo
from utils.logger import get_logger

logger = get_logger(__name__)

_RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


class ItemTriagem(BaseModel):
    """Item extraído da mensagem do comprador, exatamente como foi dito."""

    produto: str = Field(description="Nome do produto como o comprador escreveu (ex.: 'queijo coalho').")
    quantidade: float | None = Field(
        default=None,
        description="Quantidade numérica. Deixe vazio se o comprador não disse (NUNCA estime).",
    )
    unidade: str | None = Field(
        default=None,
        description="Unidade dita pelo comprador (kg, maços, unidades, dúzias, caixas). Vazio se não disse.",
    )
    organico: bool = Field(
        default=False, description="True somente se o comprador pediu explicitamente produto orgânico."
    )


# ---------- acesso aos serviços (substituível nos testes) ----------

@lru_cache
def get_triagem_service() -> TriagemService:
    return TriagemService()


@lru_cache
def get_pedido_service() -> PedidoService:
    return PedidoService()


def _erro(mensagem: str) -> dict[str, Any]:
    return {"status": "erro", "mensagem": mensagem}


def _parse_data(valor: str | None) -> date:
    """Data de referência em AAAA-MM-DD; vazio = hoje."""
    if not valor or not valor.strip():
        return date.today()
    return date.fromisoformat(valor.strip())


# ---------- ferramentas do Agente de Pedidos ----------

def obter_data_atual() -> dict[str, Any]:
    """Informa a data de hoje e o dia da semana.

    Use SEMPRE antes de interpretar um prazo relativo ("sexta", "amanhã", "semana que vem"),
    pois você não conhece a data atual. Não calcule datas de cabeça.

    Returns:
        Dicionário com "status", "data" (AAAA-MM-DD) e "dia_semana".
    """
    hoje = date.today()
    return {"status": "sucesso", "data": hoje.isoformat(), "dia_semana": NOMES_DIAS_PT[hoje.weekday()]}


def resolver_prazo_pedido(expressao: str, data_referencia: str = "") -> dict[str, Any]:
    """Converte um prazo dito pelo comprador em uma data real.

    Use para qualquer prazo ("hoje", "amanhã", "pra sexta", "04/nov", "semana que vem").
    Se o resultado for "ambiguo" ou "nao_reconhecido", NÃO escolha uma data: peça ao comprador.

    Args:
        expressao: O prazo exatamente como foi escrito (ex.: "pra sexta").
        data_referencia: Data de "hoje" em AAAA-MM-DD. Deixe vazio para usar a data atual;
            informe a data de recebimento ao reprocessar um pedido antigo.

    Returns:
        Dicionário com "status", "resultado" ("resolvido", "ambiguo" ou "nao_reconhecido"),
        "data", "dia_semana" e "explicacao".
    """
    try:
        ref = _parse_data(data_referencia)
    except ValueError:
        return _erro("data_referencia inválida. Use o formato AAAA-MM-DD.")
    prazo = resolver_prazo(expressao, ref)
    return {
        "status": "sucesso",
        "resultado": prazo.status,
        "data": prazo.data.isoformat() if prazo.data else None,
        "dia_semana": prazo.dia_semana,
        "explicacao": prazo.explicacao,
        "data_referencia": ref.isoformat(),
    }


def triar_pedido(
    itens: list[ItemTriagem],
    comprador: str = "",
    prazo: str = "",
    tipo: str = "",
    urgencia_sinalizada: bool = False,
    data_referencia: str = "",
) -> dict[str, Any]:
    """Valida um pedido em código: catálogo, safra, capacidade, preço, produtores e ausências.

    Use depois de extrair os itens da mensagem. É esta ferramenta (e não você) que decide se um
    produto está em safra ou se a quantidade cabe nos produtores. Apresente os alertas e as
    "informacoes_ausentes" retornados; nunca confirme o pedido.

    Args:
        itens: Itens extraídos da mensagem, sem inventar quantidades nem unidades.
        comprador: Nome do comprador, se identificado. Vazio se não identificado.
        prazo: Prazo como o comprador escreveu (ex.: "sexta", "04/nov"). Vazio se não disse.
        tipo: Um de "pedido_firme", "cotacao", "fornecimento_recorrente" ou "nao_e_pedido".
            Vazio se não for possível classificar.
        urgencia_sinalizada: True se o comprador declarou urgência (ex.: "urgente", "pra hoje").
        data_referencia: Data de "hoje" em AAAA-MM-DD; vazio usa a data atual.

    Returns:
        Dicionário com "status" e "pedido" (itens validados, alertas, informações ausentes,
        tipo, urgência e valor estimado) ou "mensagem" em caso de erro.
    """
    if not itens:
        return _erro("Informe ao menos um item para a triagem.")
    try:
        ref = _parse_data(data_referencia)
        entradas = [
            ItemPedidoEntrada(
                produto_informado=i.produto.strip(),
                quantidade=Decimal(str(i.quantidade)) if i.quantidade is not None else None,
                unidade_informada=(i.unidade or "").strip() or None,
                organico=i.organico,
            )
            for i in itens
            if i.produto and i.produto.strip()
        ]
        if not entradas:
            return _erro("Nenhum item com nome de produto foi informado.")
        pedido = get_triagem_service().triar(
            entradas,
            comprador=comprador.strip() or None,
            prazo_informado=prazo.strip() or None,
            data_referencia=ref,
            tipo=tipo.strip() or None,
            urgencia_sinalizada=urgencia_sinalizada,
        )
    except (ValueError, InvalidOperation) as exc:
        logger.warning("triar_pedido: entrada inválida (%s)", type(exc).__name__)
        return _erro(f"Entrada inválida: {exc}")
    except OSError:
        logger.error("triar_pedido: falha ao ler os dados da cooperativa")
        return _erro("Não foi possível consultar os dados da cooperativa agora. Tente novamente.")

    resultado: dict[str, Any] = {"status": "sucesso", "pedido": pedido.model_dump(mode="json")}
    if prazo.strip():
        p = resolver_prazo(prazo, ref)
        resultado["prazo"] = {"resultado": p.status, "explicacao": p.explicacao}
    return resultado


def consultar_pedido_recebido(pedido_id: str) -> dict[str, Any]:
    """Busca um pedido já recebido pela cooperativa (ex.: "PED-2026-005") para triagem.

    Use quando o usuário citar o código de um pedido. Devolve o texto original e a data de
    recebimento (use-a como "data_referencia" ao triar). CPFs são omitidos.

    Args:
        pedido_id: Código do pedido, no formato PED-AAAA-NNN.

    Returns:
        Dicionário com "status" e, em caso de sucesso, os dados brutos do pedido.
    """
    codigo = (pedido_id or "").strip().upper()
    if not re.fullmatch(r"PED-\d{4}-\d{3}", codigo):
        return _erro("Código inválido. Use o formato PED-AAAA-NNN (ex.: PED-2026-005).")
    try:
        bruto = get_pedido_service().buscar_pedido_bruto(codigo)
    except OSError:
        logger.error("consultar_pedido_recebido: falha ao ler os pedidos")
        return _erro("Não foi possível consultar os pedidos agora. Tente novamente.")
    if bruto is None:
        return _erro(f"Pedido {codigo} não encontrado.")
    return {
        "status": "sucesso",
        "pedido_id": bruto.id,
        "data_recebimento": bruto.data_recebimento.isoformat(),
        "data_referencia": bruto.data_recebimento.date().isoformat(),
        "canal": bruto.canal,
        "comprador": bruto.comprador,
        "situacao": bruto.status,
        "mensagem_original": _RE_CPF.sub("[CPF omitido]", bruto.mensagem_original),
    }


FERRAMENTAS_PEDIDOS = [obter_data_atual, resolver_prazo_pedido, triar_pedido, consultar_pedido_recebido]
