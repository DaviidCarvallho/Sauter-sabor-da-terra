"""Serviço de relatórios.

Função:
    Calcula os dados do resumo individual e da notificação de um produtor
    com precisão monetária (Decimal) e agrupamento por unidade real.

Responsabilidades:
    - Calcular total vendido, total pago, pendente em aberto e pendente em atraso
    - Agrupar quantidades vendidas por (produto, unidade) sem misturar unidades distintas
    - Tratar produtores inativos ou sem transações (ex.: P015) sem falhar
    - Gerar alertas objetivos (inativo, sem vendas, atraso financeiro, certificação vencida/vencendo)

Não deve:
    - Enviar notificações ou acessar arquivos diretamente
    - Usar float em valores monetários

Relações:
    Usa:        services.produtor_service, models.relatorio_model
    Usado por:  agents.tools, api.produtores_controller
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from models.produtor_model import Transacao
from models.relatorio_model import (
    DadosNotificacaoProdutor,
    RelatorioProdutor,
    ResumoProdutoVendido,
)
from services.produtor_service import ProdutorService

ZERO = Decimal("0.00")


class RelatorioService:
    """Cálculos determinísticos de vendas, pendências e dados para notificação."""

    def __init__(self, produtor_service: ProdutorService | None = None) -> None:
        self._produtor_service = produtor_service or ProdutorService()

    def gerar_relatorio_produtor(
        self,
        produtor_id: str,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        data_referencia: date | None = None,
    ) -> RelatorioProdutor:
        """Calcula o resumo individual completo do produtor na data de referência."""
        ref = data_referencia or date.today()
        dossie = self._produtor_service.obter_dossie(
            produtor_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            data_referencia=ref,
        )
        produtor = dossie.produtor
        transacoes = dossie.transacoes

        total_vendas = sum((t.valor_total for t in transacoes), ZERO)
        pagas = [t for t in transacoes if t.status_pagamento == "pago"]
        pendentes = [t for t in transacoes if t.status_pagamento == "pendente"]

        em_atraso = [t for t in pendentes if t.data_vencimento < ref]
        a_vencer = [t for t in pendentes if t.data_vencimento >= ref]

        total_pago = sum((t.valor_total for t in pagas), ZERO)
        total_pendente = sum((t.valor_total for t in pendentes), ZERO)
        total_em_atraso = sum((t.valor_total for t in em_atraso), ZERO)

        agrupado: dict[tuple[str, str], list[Transacao]] = defaultdict(list)
        for t in transacoes:
            unidade = t.unidade or "kg"
            agrupado[(t.produto, unidade)].append(t)

        produtos_vendidos = [
            ResumoProdutoVendido(
                produto=produto,
                unidade=unidade,
                quantidade_total=sum((item.quantidade for item in itens), Decimal("0")),
                valor_total=sum((item.valor_total for item in itens), ZERO),
                numero_vendas=len(itens),
            )
            for (produto, unidade), itens in sorted(agrupado.items())
        ]

        alertas: list[str] = []
        if produtor.status == "inativo":
            alertas.append(f"Produtor {produtor.id} está com status inativo no cadastro.")

        if not transacoes:
            alertas.append("Nenhuma transação registrada no período consultado.")

        if dossie.certificacao.status == "vencida" and dossie.certificacao.validade_certificacao is not None:
            alertas.append(
                f"Certificação orgânica vencida em {dossie.certificacao.validade_certificacao.strftime('%d/%m/%Y')}."
            )
        elif dossie.certificacao.status == "vencendo_em_breve" and dossie.certificacao.validade_certificacao is not None:
            alertas.append(
                f"Certificação orgânica vence em breve ({dossie.certificacao.validade_certificacao.strftime('%d/%m/%Y')})."
            )

        if em_atraso:
            alertas.append(
                f"Há {len(em_atraso)} pagamento(s) pendente(s) vencido(s) antes de {ref.strftime('%d/%m/%Y')}, totalizando R$ {total_em_atraso:.2f}."
            )

        return RelatorioProdutor(
            produtor_id=produtor.id,
            produtor_nome=produtor.nome,
            municipio=produtor.municipio,
            status_produtor=produtor.status,
            data_referencia=ref,
            data_inicio=data_inicio,
            data_fim=data_fim,
            certificacao=dossie.certificacao,
            total_vendas=total_vendas,
            total_pago=total_pago,
            total_pendente=total_pendente,
            total_em_atraso=total_em_atraso,
            quantidade_transacoes=len(transacoes),
            transacoes_pagas=len(pagas),
            transacoes_pendentes=len(pendentes),
            transacoes_em_atraso=em_atraso,
            transacoes_a_vencer=a_vencer,
            produtos_vendidos=produtos_vendidos,
            lotes_entregues=len(dossie.lotes),
            pedidos_relacionados=dossie.pedidos_relacionados,
            alertas=alertas,
        )

    def preparar_dados_notificacao(
        self,
        produtor_id: str,
        *,
        data_referencia: date | None = None,
    ) -> DadosNotificacaoProdutor:
        """Organiza os números verificados para o agente redigir a notificação."""
        relatorio = self.gerar_relatorio_produtor(
            produtor_id,
            data_referencia=data_referencia,
        )
        itens_pendentes = relatorio.transacoes_em_atraso + relatorio.transacoes_a_vencer

        return DadosNotificacaoProdutor(
            produtor_id=relatorio.produtor_id,
            produtor_nome=relatorio.produtor_nome,
            status_produtor=relatorio.status_produtor,
            data_referencia=relatorio.data_referencia,
            total_vendas=relatorio.total_vendas,
            total_pendente=relatorio.total_pendente,
            total_em_atraso=relatorio.total_em_atraso,
            quantidade_pendencias=relatorio.transacoes_pendentes,
            certificacao_status=relatorio.certificacao.status,
            validade_certificacao=relatorio.certificacao.validade_certificacao,
            itens_pendentes=itens_pendentes,
        )