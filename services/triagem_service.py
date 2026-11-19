"""Serviço de triagem de pedidos (camada determinística de David).

Função:
    Complementa o PedidoService: resolve prazos relativos a partir de uma data de
    referência confiável, classifica urgência e tipo, e consolida o PedidoEstruturado
    final que o Agente de Pedidos apresenta. O LLM interpreta o texto; aqui o código verifica.

Responsabilidades:
    - Resolver expressões de prazo ("hoje", "amanhã", "sexta", "05/11") em data real
    - Marcar como ambígua toda expressão sem dia determinado (ex.: "semana que vem")
    - Classificar urgência por regra explícita (dias até a entrega ou sinalização do comprador)
    - Validar o vocabulário de 'tipo' (o LLM escolhe; o código só aceita valores conhecidos)
    - Registrar informações ausentes: unidade, prazo ambíguo/passado, capacidade não comprovada

Não deve:
    - Interpretar linguagem natural livre (função do agente)
    - Ler arquivos ou repositórios diretamente (usa PedidoService)
    - Confirmar pedido nem alocar produtores

Relações:
    Usa:        services.pedido_service, models.pedido_model, repositories.storage_repository
    Usado por:  agents.tools

Decisões pendentes de validação pela equipe (não estão nos dados nem nos contratos):
    - Vocabulário de 'tipo' (TIPOS_PEDIDO): derivado dos 15 pedidos de pedidos.json
    - Limiares de urgência (LIMITE_URGENTE_DIAS, LIMITE_PLANEJADO_DIAS)
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from models.pedido_model import ItemPedidoEntrada, PedidoEstruturado
from repositories.storage_repository import normalizar_texto
from services.pedido_service import DIAS_SEMANA_PT, NOMES_DIAS_PT, PedidoService
from utils.logger import get_logger

logger = get_logger(__name__)

# Vocabulário de tipo, derivado dos pedidos reais:
#   pedido_firme            -> compra com itens/quantidades/prazo (PED-001, 002, 004, 006)
#   cotacao                 -> pede preço/disponibilidade antes de comprar (PED-007, 008, 009, 013)
#   fornecimento_recorrente -> contrato semanal/mensal (PED-010, 011)
#   nao_e_pedido            -> mensagem de outra natureza (produtor, fiscalização: PED-012, 014, 015)
TIPOS_PEDIDO: tuple[str, ...] = (
    "pedido_firme",
    "cotacao",
    "fornecimento_recorrente",
    "nao_e_pedido",
)

URGENCIAS: tuple[str, ...] = ("urgente", "normal", "planejado", "indefinida")

# Limiares propostos (a validar): entrega em até 2 dias ou sinalizada pelo comprador = urgente;
# acima de 14 dias = planejado; entre os dois = normal.
LIMITE_URGENTE_DIAS = 2
LIMITE_PLANEJADO_DIAS = 14

_MESES_PT: dict[str, int] = {
    "jan": 1, "janeiro": 1, "fev": 2, "fevereiro": 2, "mar": 3, "marco": 3,
    "abr": 4, "abril": 4, "mai": 5, "maio": 5, "jun": 6, "junho": 6,
    "jul": 7, "julho": 7, "ago": 8, "agosto": 8, "set": 9, "setembro": 9,
    "out": 10, "outubro": 10, "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12,
}

_RE_DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_DATA_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
_RE_DATA_MES = re.compile(
    r"\b(\d{1,2})\s*(?:de\s+|/)?\s*(" + "|".join(_MESES_PT) + r")\b(?:\s*(?:de\s+|/)?\s*(\d{4}))?"
)
_EXPRESSOES_AMBIGUAS = (
    "semana que vem", "proxima semana", "semana q vem", "proximo mes", "mes que vem",
    "essa semana", "esta semana", "o quanto antes", "quanto antes", "quando puder",
)


class PrazoResolvido(BaseModel):
    """Resultado da resolução de uma expressão de prazo."""

    model_config = ConfigDict(frozen=True)

    expressao: str
    status: Literal["resolvido", "ambiguo", "nao_reconhecido"]
    data: date | None = None
    dia_semana: str | None = None
    explicacao: str


def _resolvido(expr: str, data: date, como: str) -> PrazoResolvido:
    return PrazoResolvido(
        expressao=expr,
        status="resolvido",
        data=data,
        dia_semana=NOMES_DIAS_PT[data.weekday()],
        explicacao=como,
    )


def resolver_prazo(expressao: str, data_referencia: date) -> PrazoResolvido:
    """Converte uma expressão de prazo em data, usando `data_referencia` como "hoje".

    Regras: data explícita vence qualquer outra pista; "hoje/amanhã/depois de amanhã" são
    exatos; um dia da semana resolve para a próxima ocorrência futura (se for o mesmo dia
    da referência, é ambíguo); expressões sem dia determinado são ambíguas.
    """
    norm = normalizar_texto(expressao or "")
    if not norm:
        return PrazoResolvido(expressao=expressao or "", status="nao_reconhecido",
                              explicacao="Prazo vazio.")

    # ISO (AAAA-MM-DD): é o formato que as nossas ferramentas devolvem e que o modelo reaproveita.
    m = _RE_DATA_ISO.search(norm)
    if m:
        try:
            alvo = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return PrazoResolvido(expressao=expressao, status="nao_reconhecido",
                                  explicacao=f"Data inválida: {m.group(0)}.")
        return _resolvido(expressao, alvo, f"Data explícita {alvo.strftime('%d/%m/%Y')}.")

    m = _RE_DATA_NUM.search(norm)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        ano = int(m.group(3)) if m.group(3) else data_referencia.year
        ano = ano + 2000 if ano < 100 else ano
        try:
            alvo = date(ano, mes, dia)
        except ValueError:
            return PrazoResolvido(expressao=expressao, status="nao_reconhecido",
                                  explicacao=f"Data inválida: {m.group(0)}.")
        if not m.group(3) and alvo < data_referencia:
            alvo = date(ano + 1, mes, dia)
        return _resolvido(expressao, alvo, f"Data explícita {alvo.strftime('%d/%m/%Y')}.")

    m = _RE_DATA_MES.search(norm)
    if m:
        dia, mes = int(m.group(1)), _MESES_PT[m.group(2)]
        ano = int(m.group(3)) if m.group(3) else data_referencia.year
        try:
            alvo = date(ano, mes, dia)
        except ValueError:
            return PrazoResolvido(expressao=expressao, status="nao_reconhecido",
                                  explicacao=f"Data inválida: {m.group(0)}.")
        if not m.group(3) and alvo < data_referencia:
            alvo = date(ano + 1, mes, dia)
        return _resolvido(expressao, alvo, f"Data explícita {alvo.strftime('%d/%m/%Y')}.")

    if any(t in norm for t in _EXPRESSOES_AMBIGUAS):
        return PrazoResolvido(expressao=expressao, status="ambiguo",
                              explicacao="Expressão sem dia determinado; peça a data exata.")

    if re.search(r"\bdepois de amanha\b", norm):
        return _resolvido(expressao, data_referencia + timedelta(days=2), "Depois de amanhã.")
    if re.search(r"\bamanha\b", norm):
        return _resolvido(expressao, data_referencia + timedelta(days=1), "Amanhã.")
    if re.search(r"\b(hoje|agora)\b", norm):
        return _resolvido(expressao, data_referencia, "Hoje.")

    # Prefere nomes mais longos ("sexta-feira") antes dos curtos ("sexta").
    for termo in sorted(DIAS_SEMANA_PT, key=len, reverse=True):
        if re.search(rf"\b{re.escape(termo)}\b", norm):
            alvo_dia = DIAS_SEMANA_PT[termo]
            delta = (alvo_dia - data_referencia.weekday()) % 7
            if delta == 0:
                return PrazoResolvido(
                    expressao=expressao, status="ambiguo",
                    explicacao=(f"'{termo}' é o mesmo dia da semana de hoje "
                                f"({data_referencia.strftime('%d/%m/%Y')}): hoje ou daqui a 7 dias?"),
                )
            return _resolvido(expressao, data_referencia + timedelta(days=delta),
                              f"Próxima {NOMES_DIAS_PT[alvo_dia]}.")

    return PrazoResolvido(expressao=expressao, status="nao_reconhecido",
                          explicacao="Não foi possível identificar uma data na expressão.")


def classificar_urgencia(
    data_entrega: date | None,
    data_referencia: date,
    *,
    sinalizada_pelo_comprador: bool = False,
) -> str:
    """Urgência por regra explícita; sem data e sem sinalização, 'indefinida'."""
    if sinalizada_pelo_comprador:
        return "urgente"
    if data_entrega is None:
        return "indefinida"
    dias = (data_entrega - data_referencia).days
    if dias < 0:
        return "indefinida"
    if dias <= LIMITE_URGENTE_DIAS:
        return "urgente"
    if dias > LIMITE_PLANEJADO_DIAS:
        return "planejado"
    return "normal"


def validar_tipo(tipo: str | None) -> str | None:
    """Aceita só valores de TIPOS_PEDIDO (ValueError caso contrário)."""
    if tipo is None or not tipo.strip():
        return None
    valor = normalizar_texto(tipo).replace(" ", "_")
    if valor not in TIPOS_PEDIDO:
        raise ValueError(f"Tipo '{tipo}' inválido. Use um destes: {', '.join(TIPOS_PEDIDO)}.")
    return valor


class TriagemService:
    """Triagem completa: prazo + validações do PedidoService + urgência + tipo."""

    def __init__(self, pedido_service: PedidoService | None = None) -> None:
        self._pedidos = pedido_service or PedidoService()

    def triar(
        self,
        itens: list[ItemPedidoEntrada],
        *,
        comprador: str | None = None,
        prazo_informado: str | None = None,
        data_referencia: date,
        tipo: str | None = None,
        urgencia_sinalizada: bool = False,
        pedido_id: str | None = None,
    ) -> PedidoEstruturado:
        """Valida os itens e devolve o pedido estruturado com tipo e urgência.

        Levanta ValueError para `tipo` fora do vocabulário.
        """
        tipo_ok = validar_tipo(tipo)

        prazo = (
            resolver_prazo(prazo_informado, data_referencia) if prazo_informado else None
        )
        data_entrega = prazo.data if prazo and prazo.status == "resolvido" else None

        pedido = self._pedidos.estruturar_pedido(
            itens,
            pedido_id=pedido_id,
            comprador=comprador,
            prazo_informado=prazo_informado,
            data_entrega_prevista=data_entrega,
            data_referencia=data_referencia,
        )

        ausentes = list(pedido.informacoes_ausentes)
        if prazo is not None and prazo.status != "resolvido":
            ausentes.append(f"prazo_{prazo.status}")
        if data_entrega is not None and data_entrega < data_referencia:
            ausentes.append("prazo_no_passado")

        for item_in, item_val in zip(itens, pedido.itens, strict=True):
            if item_val.quantidade is not None and not item_in.unidade_informada:
                ausentes.append(f"unidade:{item_val.produto_informado}")
            if (
                item_val.encontrado
                and item_val.quantidade is not None
                and item_val.capacidade_referencia is None
            ):
                ausentes.append(f"capacidade_nao_comprovada:{item_val.produto_informado}")

        # Unidade diferente da tabela de preços (ex.: "caixas" x kg): sem fator de conversão
        # nos dados, o valor estimado não é confiável e não deve ser apresentado.
        itens_ok = []
        for item_in, item_val in zip(itens, pedido.itens, strict=True):
            if any(a.tipo == "unidade_divergente" for a in item_val.alertas):
                itens_ok.append(item_val.model_copy(update={
                    "unidade": item_in.unidade_informada, "valor_estimado": None,
                    "desconto_atacado_pct": 0, "desconto_aplicado": False,
                }))
                ausentes.append(f"conversao_unidade:{item_val.produto_informado}")
            else:
                itens_ok.append(item_val)
        valores = [i.valor_estimado for i in itens_ok if i.valor_estimado is not None]
        pedido = pedido.model_copy(update={
            "itens": itens_ok,
            "valor_total_estimado": sum(valores, Decimal("0.00")) if valores else None,
        })

        urgencia = classificar_urgencia(
            data_entrega, data_referencia, sinalizada_pelo_comprador=urgencia_sinalizada
        )
        logger.info("Triagem: %d item(ns), urgência=%s, tipo=%s", len(itens), urgencia, tipo_ok)

        return pedido.model_copy(
            update={"tipo": tipo_ok, "urgencia": urgencia, "informacoes_ausentes": ausentes}
        )
