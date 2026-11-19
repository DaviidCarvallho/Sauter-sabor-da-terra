"""Serviço de pedidos.

Função:
    Validações determinísticas da triagem: o LLM (David) interpreta o texto,
    este serviço verifica os fatos nos dados da cooperativa.

Responsabilidades:
    - Consultar e normalizar produto contra sazonalidade e tabela de preços
    - Verificar nível de safra no mês de entrega/referência
    - Selecionar produtores ativos e checar certificação orgânica vigente (60 dias)
    - Calcular preços convencional/orgânico e desconto por atacado em Decimal
    - Aplicar restrições documentadas nas observações (sem SIE, exclusividade P0xx)
    - Conferir capacidade híbrida (limite explícito nas observações ou maior lote histórico)
    - Detectar divergência entre dia da semana citado e data explícita
    - Montar o PedidoEstruturado factual mantendo 'tipo' e 'urgencia' abertos para David

Não deve:
    - Interpretar linguagem natural (função do agente)
    - Ler arquivos diretamente

Relações:
    Usa:        repositories.pedido_repository, repositories.produtor_repository,
                repositories.produto_repository, repositories.lote_repository,
                services.produtor_service, models.pedido_model
    Usado por:  agents.tools, api.pedidos_controller
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from models.pedido_model import (
    AlertaTriagem,
    ItemPedidoEntrada,
    ItemPedidoValidado,
    PedidoBruto,
    PedidoEstruturado,
    ProdutorElegivel,
)
from models.produto_model import PrecoProduto, SazonalidadeProduto
from repositories.lote_repository import LoteRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produto_repository import ProdutoRepository
from repositories.produtor_repository import ProdutorRepository
from repositories.storage_repository import normalizar_texto
from services.produtor_service import ProdutorService

MESES_COLUNA: dict[int, str] = {
    1: "jan",
    2: "fev",
    3: "mar",
    4: "abr",
    5: "mai",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "set",
    10: "out",
    11: "nov",
    12: "dez",
}

DIAS_SEMANA_PT: dict[str, int] = {
    "segunda": 0,
    "segunda-feira": 0,
    "terca": 1,
    "terca-feira": 1,
    "quarta": 2,
    "quarta-feira": 2,
    "quinta": 3,
    "quinta-feira": 3,
    "sexta": 4,
    "sexta-feira": 4,
    "sabado": 5,
    "domingo": 6,
}

NOMES_DIAS_PT: dict[int, str] = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}

SINONIMOS_UNIDADE: dict[str, str] = {
    "kg": "kg",
    "quilo": "kg",
    "quilos": "kg",
    "unidade": "unidade",
    "unidades": "unidade",
    "un": "unidade",
    "unid": "unidade",
    "maco": "maço",
    "macos": "maço",
    "litro": "litro",
    "litros": "litro",
    "l": "litro",
    "duzia": "dúzia",
    "duzias": "dúzia",
    "dz": "dúzia",
}


class PedidoService:
    """Consultas determinísticas aos dados para apoiar a triagem de pedidos."""

    def __init__(
        self,
        pedido_repo: PedidoRepository | None = None,
        produtor_repo: ProdutorRepository | None = None,
        produto_repo: ProdutoRepository | None = None,
        lote_repo: LoteRepository | None = None,
        produtor_service: ProdutorService | None = None,
    ) -> None:
        self._pedido_repo = pedido_repo or PedidoRepository()
        self._produtor_repo = produtor_repo or ProdutorRepository()
        self._produto_repo = produto_repo or ProdutoRepository()
        self._lote_repo = lote_repo or LoteRepository()
        self._produtor_service = produtor_service or ProdutorService(
            produtor_repo=self._produtor_repo,
            pedido_repo=self._pedido_repo,
            lote_repo=self._lote_repo,
            produto_repo=self._produto_repo,
        )

    def listar_pedidos_brutos(self) -> list[PedidoBruto]:
        return self._pedido_repo.listar()

    def buscar_pedido_bruto(self, pedido_id: str) -> PedidoBruto | None:
        return self._pedido_repo.buscar_por_id(pedido_id)

    @staticmethod
    def _extrair_limite_explicito(
        sazonalidade: SazonalidadeProduto | None,
    ) -> tuple[Decimal, str] | None:
        """Extrai limites numéricos explícitos das observações (ex.: '~80kg/semana')."""
        if sazonalidade is None or not sazonalidade.observacao:
            return None
        match = re.search(
            r"~?\s*(\d+(?:[.,]\d+)?)\s*(kg|d[úu]zias?|unidades?|ma[çc]os?|litros?)\s*/\s*semana",
            sazonalidade.observacao,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        valor = Decimal(match.group(1).replace(",", "."))
        return valor, f"limite explícito na observação ({sazonalidade.observacao})"

    def _referencia_capacidade(
        self,
        produto_canonico: str,
        sazonalidade: SazonalidadeProduto | None,
    ) -> tuple[Decimal | None, str | None]:
        """Regra híbrida: limite explícito nas observações ou maior lote histórico."""
        explicito = self._extrair_limite_explicito(sazonalidade)
        if explicito is not None:
            return explicito

        lotes = self._lote_repo.listar_por_produto(produto_canonico)
        if not lotes:
            return None, None

        maior_lote = max(lote.quantidade for lote in lotes)
        return maior_lote, "maior volume registrado no histórico de lotes"

    @staticmethod
    def _extrair_restricoes_observacoes(
        sazonalidade: SazonalidadeProduto | None,
        precos: list[PrecoProduto],
    ) -> tuple[list[str], set[str], bool]:
        """Lê restrições documentadas em texto livre (sem SIE, apenas P0xx)."""
        restricoes: list[str] = []
        exclusivos: set[str] = set()
        sem_sie = False

        textos = []
        if sazonalidade and sazonalidade.observacao:
            textos.append(sazonalidade.observacao)
        for p in precos:
            if p.observacao:
                textos.append(p.observacao)

        for texto in textos:
            norm = normalizar_texto(texto)
            if "sem sie" in norm or "venda direta apenas" in norm:
                sem_sie = True
                if texto not in restricoes:
                    restricoes.append(texto)

            for m in re.finditer(r"apenas\s+(p0\d{2})", texto, flags=re.IGNORECASE):
                exclusivos.add(m.group(1).upper())
                if texto not in restricoes:
                    restricoes.append(texto)

        return restricoes, exclusivos, sem_sie

    def validar_item(
        self,
        item: ItemPedidoEntrada,
        *,
        data_entrega: date | None = None,
        data_referencia: date | None = None,
    ) -> ItemPedidoValidado:
        """Executa todas as validações determinísticas para um item do pedido."""
        ref = data_referencia or date.today()
        data_safra = data_entrega or ref
        mes_col = MESES_COLUNA[data_safra.month]

        sazonalidade = self._produto_repo.buscar_sazonalidade(item.produto_informado)
        precos = self._produto_repo.listar_precos_por_produto(item.produto_informado)

        if sazonalidade is None and not precos:
            return ItemPedidoValidado(
                produto_informado=item.produto_informado,
                encontrado=False,
                quantidade=item.quantidade,
                unidade=item.unidade_informada,
                organico_solicitado=item.organico,
                mes_referencia=mes_col,
                alertas=[
                    AlertaTriagem(
                        tipo="produto_nao_encontrado",
                        mensagem=(
                            f"Produto '{item.produto_informado}' não possui dados de safra nem de preço no catálogo."
                        ),
                        severidade="alta",
                        produto=item.produto_informado,
                    )
                ],
            )

        produto_canonico = sazonalidade.produto if sazonalidade else precos[0].produto
        unidade_oficial = precos[0].unidade if precos else None
        alertas: list[AlertaTriagem] = []

        if item.unidade_informada and unidade_oficial:
            u_norm = normalizar_texto(
                SINONIMOS_UNIDADE.get(
                    normalizar_texto(item.unidade_informada),
                    normalizar_texto(item.unidade_informada),
                )
            )
            if u_norm != normalizar_texto(unidade_oficial):
                alertas.append(
                    AlertaTriagem(
                        tipo="unidade_divergente",
                        mensagem=(
                            f"Unidade informada ('{item.unidade_informada}') difere da unidade da tabela de preços ('{unidade_oficial}') para {produto_canonico}."
                        ),
                        severidade="media",
                        produto=produto_canonico,
                    )
                )

        nivel_safra = getattr(sazonalidade, mes_col) if sazonalidade is not None else None
        obs_safra = f" ({sazonalidade.observacao})" if sazonalidade and sazonalidade.observacao else ""
        if nivel_safra == "nenhuma":
            alertas.append(
                AlertaTriagem(
                    tipo="fora_de_safra",
                    mensagem=f"{produto_canonico} está fora de safra em {mes_col}{obs_safra}.",
                    severidade="alta",
                    produto=produto_canonico,
                )
            )
        elif nivel_safra == "baixa":
            alertas.append(
                AlertaTriagem(
                    tipo="baixa_disponibilidade",
                    mensagem=f"{produto_canonico} está em safra baixa em {mes_col}{obs_safra}.",
                    severidade="media",
                    produto=produto_canonico,
                )
            )

        restricoes, exclusivos, sem_sie = self._extrair_restricoes_observacoes(sazonalidade, precos)
        if sem_sie:
            alertas.append(
                AlertaTriagem(
                    tipo="restricao_sanitaria_sie",
                    mensagem=f"{produto_canonico} possui restrição sanitária (sem SIE para revenda; venda direta apenas).",
                    severidade="alta",
                    produto=produto_canonico,
                )
            )
        if exclusivos:
            alertas.append(
                AlertaTriagem(
                    tipo="exclusividade_produtor",
                    mensagem=f"Fornecimento de {produto_canonico} restrito a produtor específico ({', '.join(sorted(exclusivos))}).",
                    severidade="info",
                    produto=produto_canonico,
                )
            )

        produtores_candidatos = self._produtor_service.listar_produtores_por_produto(
            item.produto_informado,
            apenas_ativos=True,
            apenas_organicos_vigentes=False,
            data_referencia=ref,
        )
        if exclusivos:
            produtores_candidatos = [
                p for p in produtores_candidatos if p.id.upper() in exclusivos
            ]

        produtores_elegiveis: list[ProdutorElegivel] = []
        for p in produtores_candidatos:
            sit = self._produtor_service.avaliar_certificacao(p, data_referencia=ref)
            vigente = sit.status in {"vigente", "vencendo_em_breve"}
            if sit.status == "vencida" and p.validade_certificacao is not None:
                alertas.append(
                    AlertaTriagem(
                        tipo="certificacao_vencida",
                        mensagem=(
                            f"Produtor {p.nome} ({p.id}) está com certificação orgânica vencida desde {p.validade_certificacao.strftime('%d/%m/%Y')}."
                        ),
                        severidade="media",
                        produto=produto_canonico,
                    )
                )
            if not item.organico or vigente:
                produtores_elegiveis.append(
                    ProdutorElegivel(
                        id=p.id,
                        nome=p.nome,
                        municipio=p.municipio,
                        certificacao_organica=p.certificacao_organica,
                        certificacao_vigente=vigente,
                        validade_certificacao=p.validade_certificacao,
                    )
                )

        preco_ref = precos[0] if precos else None
        preco_unitario: Decimal | None = None
        desconto_pct = 0
        desconto_aplicado = False
        valor_estimado: Decimal | None = None

        if preco_ref is not None:
            preco_unitario = (
                preco_ref.preco_organico if item.organico else preco_ref.preco_convencional
            )
            if item.organico and (preco_ref.preco_organico is None or not produtores_elegiveis):
                alertas.append(
                    AlertaTriagem(
                        tipo="certificacao_organica_indisponivel",
                        mensagem=(
                            f"Não há oferta orgânica consistente para {produto_canonico} (preço orgânico ou produtor com certificação vigente ausente)."
                        ),
                        severidade="alta",
                        produto=produto_canonico,
                    )
                )
                if preco_ref.preco_organico is not None and not produtores_elegiveis:
                    preco_unitario = None

            if preco_unitario is not None and item.quantidade is not None:
                if (
                    preco_ref.volume_minimo_atacado > 0
                    and preco_ref.desconto_atacado_pct > 0
                    and item.quantidade >= preco_ref.volume_minimo_atacado
                ):
                    desconto_pct = preco_ref.desconto_atacado_pct
                    desconto_aplicado = True
                    fator = Decimal(100 - desconto_pct) / Decimal(100)
                    valor_estimado = (item.quantidade * preco_unitario * fator).quantize(
                        Decimal("0.01")
                    )
                else:
                    valor_estimado = (item.quantidade * preco_unitario).quantize(Decimal("0.01"))

        cap_ref, cap_origem = self._referencia_capacidade(produto_canonico, sazonalidade)
        if item.quantidade is not None and cap_ref is not None and item.quantidade > cap_ref:
            unidade_texto = unidade_oficial or item.unidade_informada or "unidades"
            alertas.append(
                AlertaTriagem(
                    tipo="quantidade_acima_capacidade",
                    mensagem=(
                        f"Quantidade solicitada ({item.quantidade} {unidade_texto}) supera a referência de {cap_ref} {unidade_texto} ({cap_origem})."
                    ),
                    severidade="media",
                    produto=produto_canonico,
                )
            )

        if item.quantidade is None:
            alertas.append(
                AlertaTriagem(
                    tipo="informacao_ausente",
                    mensagem=f"Quantidade não informada para '{item.produto_informado}'.",
                    severidade="info",
                    produto=produto_canonico,
                )
            )

        return ItemPedidoValidado(
            produto_informado=item.produto_informado,
            produto_normalizado=produto_canonico,
            variedade_preco=preco_ref.produto if preco_ref else None,
            encontrado=True,
            quantidade=item.quantidade,
            unidade=unidade_oficial or item.unidade_informada,
            organico_solicitado=item.organico,
            nivel_safra=nivel_safra,
            mes_referencia=mes_col,
            preco_unitario=preco_unitario,
            desconto_atacado_pct=desconto_pct,
            desconto_aplicado=desconto_aplicado,
            valor_estimado=valor_estimado,
            produtores_elegiveis=produtores_elegiveis,
            capacidade_referencia=cap_ref,
            origem_capacidade=cap_origem,
            restricoes=restricoes,
            alertas=alertas,
        )

    @staticmethod
    def verificar_divergencia_data(
        texto_prazo: str,
        data_explicitada: date,
    ) -> AlertaTriagem | None:
        """Detecta quando o dia da semana citado contradiz a data explícita (ex.: 'sexta (01/nov)')."""
        norm = normalizar_texto(texto_prazo)
        dia_citado: int | None = None
        for termo, idx in DIAS_SEMANA_PT.items():
            if re.search(rf"\b{re.escape(termo)}\b", norm):
                dia_citado = idx
                break

        if dia_citado is None:
            return None

        dia_real = data_explicitada.weekday()
        if dia_citado != dia_real:
            return AlertaTriagem(
                tipo="data_inconsistente",
                mensagem=(
                    f"Divergência de calendário em '{texto_prazo}': a data {data_explicitada.strftime('%d/%m/%Y')} cai em {NOMES_DIAS_PT[dia_real]}, não no dia da semana citado."
                ),
                severidade="alta",
            )
        return None

    def estruturar_pedido(
        self,
        itens: list[ItemPedidoEntrada],
        *,
        pedido_id: str | None = None,
        comprador: str | None = None,
        prazo_informado: str | None = None,
        data_entrega_prevista: date | None = None,
        data_referencia: date | None = None,
        tipo: str | None = None,
        urgencia: str | None = None,
    ) -> PedidoEstruturado:
        """Consolida a validação determinística dos itens e o contexto factual do pedido."""
        ref = data_referencia or date.today()
        itens_validados = [
            self.validar_item(
                item,
                data_entrega=data_entrega_prevista,
                data_referencia=ref,
            )
            for item in itens
        ]

        alertas_gerais: list[AlertaTriagem] = []
        informacoes_ausentes: list[str] = []

        if not comprador or not comprador.strip():
            informacoes_ausentes.append("comprador")
        if not prazo_informado and data_entrega_prevista is None:
            informacoes_ausentes.append("prazo")

        for item_val in itens_validados:
            if item_val.quantidade is None:
                informacoes_ausentes.append(f"quantidade:{item_val.produto_informado}")
            alertas_gerais.extend(item_val.alertas)

        if prazo_informado and data_entrega_prevista is not None:
            alerta_data = self.verificar_divergencia_data(prazo_informado, data_entrega_prevista)
            if alerta_data is not None:
                alertas_gerais.append(alerta_data)

        valores = [i.valor_estimado for i in itens_validados if i.valor_estimado is not None]
        valor_total = sum(valores, Decimal("0.00")) if valores else None

        return PedidoEstruturado(
            pedido_id=pedido_id,
            comprador=comprador,
            prazo_informado=prazo_informado,
            data_entrega_prevista=data_entrega_prevista,
            data_referencia=ref,
            tipo=tipo,
            urgencia=urgencia,
            itens=itens_validados,
            valor_total_estimado=valor_total,
            informacoes_ausentes=informacoes_ausentes,
            alertas=alertas_gerais,
        )