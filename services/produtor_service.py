"""Serviço de produtores.

Função:
    Reúne cadastro, pedidos, lotes e transações financeiras de um produtor,
    preservando a regra de não expor dados pessoais sensíveis.

Responsabilidades:
    - Consultar produtores por ID, nome ou produto (com normalização do catálogo)
    - Avaliar situação da certificação orgânica em relação a uma data de referência
    - Identificar pedidos do canal de entrada pertencentes ao produtor via telefone
    - Reunir transações e lotes enriquecidos com a unidade real de cada produto

Não deve:
    - Redigir texto final de comunicação (função do agente)
    - Expor CPF, dados bancários ou telefone nos modelos devolvidos

Relações:
    Usa:        repositories.produtor_repository, repositories.pedido_repository,
                repositories.financeiro_repository, repositories.lote_repository,
                repositories.produto_repository, models.relatorio_model
    Usado por:  services.relatorio_service, services.pedido_service, agents.tools
"""

from __future__ import annotations

from datetime import date

from models.pedido_model import PedidoBruto
from models.produto_model import Lote
from models.produtor_model import Produtor, Transacao
from models.relatorio_model import DossieProdutor, SituacaoCertificacao
from repositories.financeiro_repository import FinanceiroRepository
from repositories.lote_repository import LoteRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produto_repository import ProdutoRepository
from repositories.produtor_repository import ProdutorRepository
from repositories.storage_repository import normalizar_texto

DIAS_ALERTA_CERTIFICACAO = 60


class ProdutorService:
    """Consolida cadastro, certificação, pedidos, lotes e financeiro de produtores."""

    def __init__(
        self,
        produtor_repo: ProdutorRepository | None = None,
        pedido_repo: PedidoRepository | None = None,
        financeiro_repo: FinanceiroRepository | None = None,
        lote_repo: LoteRepository | None = None,
        produto_repo: ProdutoRepository | None = None,
    ) -> None:
        self._produtor_repo = produtor_repo or ProdutorRepository()
        self._pedido_repo = pedido_repo or PedidoRepository()
        self._financeiro_repo = financeiro_repo or FinanceiroRepository()
        self._lote_repo = lote_repo or LoteRepository()
        self._produto_repo = produto_repo or ProdutoRepository()

    @staticmethod
    def avaliar_certificacao(
        produtor: Produtor,
        *,
        data_referencia: date | None = None,
    ) -> SituacaoCertificacao:
        """Avalia vigência da certificação orgânica considerando janela preventiva de 60 dias."""
        ref = data_referencia or date.today()
        if not produtor.certificacao_organica or produtor.validade_certificacao is None:
            return SituacaoCertificacao(
                certificacao_organica=False,
                validade_certificacao=None,
                status="nao_possui",
                dias_para_vencer=None,
            )

        dias = (produtor.validade_certificacao - ref).days
        if dias < 0:
            status = "vencida"
        elif dias <= DIAS_ALERTA_CERTIFICACAO:
            status = "vencendo_em_breve"
        else:
            status = "vigente"

        return SituacaoCertificacao(
            certificacao_organica=True,
            validade_certificacao=produtor.validade_certificacao,
            status=status,
            dias_para_vencer=dias,
        )

    def listar_produtores(self, *, apenas_ativos: bool = False) -> list[Produtor]:
        return self._produtor_repo.listar(apenas_ativos=apenas_ativos)

    def buscar_produtor(self, identificador_ou_nome: str) -> Produtor | None:
        """Busca produtor por ID ('P001') ou correspondência de nome completo/tokens."""
        texto = identificador_ou_nome.strip()
        if not texto:
            return None

        por_id = self._produtor_repo.buscar_por_id(texto)
        if por_id is not None:
            return por_id

        alvo = normalizar_texto(texto)
        produtores = self._produtor_repo.listar()

        for p in produtores:
            if normalizar_texto(p.nome) == alvo:
                return p

        tokens = [t for t in alvo.split() if len(t) >= 2]
        if tokens:
            for p in produtores:
                nome_norm = normalizar_texto(p.nome)
                if all(tok in nome_norm.split() for tok in tokens):
                    return p

            for p in produtores:
                primeiro_nome = normalizar_texto(p.nome).split()[0]
                if primeiro_nome in tokens:
                    return p

        return None

    def listar_produtores_por_produto(
        self,
        produto: str,
        *,
        apenas_ativos: bool = True,
        apenas_organicos_vigentes: bool = False,
        data_referencia: date | None = None,
    ) -> list[Produtor]:
        """Lista produtores compatíveis com o produto usando normalização explícita."""
        termos_aceitos = self._produto_repo.termos_cadastro_para_produto(produto)
        if not termos_aceitos:
            return []

        ref = data_referencia or date.today()
        resultado: list[Produtor] = []

        for produtor in self._produtor_repo.listar(apenas_ativos=apenas_ativos):
            produtos_produtor = {normalizar_texto(item) for item in produtor.produtos}
            if not (produtos_produtor & termos_aceitos):
                continue

            if apenas_organicos_vigentes:
                situacao = self.avaliar_certificacao(produtor, data_referencia=ref)
                if situacao.status not in {"vigente", "vencendo_em_breve"}:
                    continue

            resultado.append(produtor)

        return resultado

    def listar_pedidos_do_produtor(self, produtor_id: str) -> list[PedidoBruto]:
        """Identifica solicitações em pedidos.json cujo remetente (telefone) pertence ao produtor."""
        alvo = normalizar_texto(produtor_id)
        pedidos_relacionados: list[PedidoBruto] = []

        for pedido in self._pedido_repo.listar():
            dono = self._produtor_repo.buscar_por_telefone(pedido.remetente)
            if dono is not None and normalizar_texto(dono.id) == alvo:
                pedidos_relacionados.append(pedido)

        return pedidos_relacionados

    def _enriquecer_unidade_transacoes(self, transacoes: list[Transacao]) -> list[Transacao]:
        return [
            t.model_copy(update={"unidade": self._produto_repo.resolver_unidade(t.produto) or "kg"})
            for t in transacoes
        ]

    def _enriquecer_unidade_lotes(self, lotes: list[Lote]) -> list[Lote]:
        return [
            lote.model_copy(update={"unidade": self._produto_repo.resolver_unidade(lote.produto) or "kg"})
            for lote in lotes
        ]

    def obter_dossie(
        self,
        produtor_id: str,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        data_referencia: date | None = None,
    ) -> DossieProdutor:
        """Reúne dados públicos, certificação, transações, lotes e pedidos de um produtor."""
        produtor = self._produtor_repo.buscar_por_id(produtor_id)
        if produtor is None:
            raise ValueError(f"Produtor não encontrado: {produtor_id}")

        ref = data_referencia or date.today()
        certificacao = self.avaliar_certificacao(produtor, data_referencia=ref)

        transacoes = self._enriquecer_unidade_transacoes(
            self._financeiro_repo.listar_por_produtor(
                produtor.id,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
        )
        lotes = self._enriquecer_unidade_lotes(
            self._lote_repo.listar_por_produtor(produtor.id)
        )
        pedidos = self.listar_pedidos_do_produtor(produtor.id)

        return DossieProdutor(
            produtor=produtor,
            certificacao=certificacao,
            transacoes=transacoes,
            lotes=lotes,
            pedidos_relacionados=pedidos,
        )