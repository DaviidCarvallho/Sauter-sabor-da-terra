"""Serviço de documentos.

Função:
    Coordena a consulta ao acervo documental (RAG) e devolve trechos com fontes.

Responsabilidades:
    - Receber a pergunta e consultar o retriever (top-k)
    - Aplicar o limiar de distância: sem trechos suficientemente próximos, a evidência é
      insuficiente e o serviço diz isso, em vez de devolver o "menos ruim"
    - Montar as fontes citáveis (documento e página, sem inventar página)

Não deve:
    - Gerar a resposta final (função do agente)
    - Conhecer ChromaDB ou embeddings (isso é do rag.vector_store)

Relações:
    Usa:        rag.retriever (por injeção), models.documento_model
    Usado por:  agents.tools, api.documentos_controller

Decisão a validar com Rawan: DISTANCIA_MAXIMA = 0.30 é o valor que os testes de qualidade do
retriever (tests/test_retriever_quality.py) já usam com os documentos reais. Calibrar com
perguntas reais quando o índice estiver construído (`python -m rag.ingestion`).

Observação:
    O Retriever é criado sob demanda: o índice e o cliente de embeddings só são acessados
    quando alguém consulta (e o servidor sobe sem o extra "rag").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.documento_model import ConsultaDocumental, FonteCitavel, TrechoDocumento
from utils.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from rag.retriever import Retriever

logger = get_logger(__name__)

DISTANCIA_MAXIMA = 0.30
TOP_K_PADRAO = 5
TOP_K_MAXIMO = 8

# O DocumentLoader grava page=1 para .txt, mas arquivo de texto não tem páginas. O contrato
# (docs/CONTRATOS_ARQUITETURAIS.md, 5.4) manda não inventar número: para .txt a página é omitida.
EXTENSOES_SEM_PAGINA = (".txt",)


def _pagina_citavel(source: str, page: int | None) -> int | None:
    return None if source.lower().endswith(EXTENSOES_SEM_PAGINA) else page


class DocumentoService:
    def __init__(self, retriever: Retriever | None = None) -> None:
        self._retriever = retriever

    def _obter_retriever(self) -> Retriever:
        if self._retriever is None:
            from rag.retriever import Retriever
            from rag.vector_store import VectorStore

            self._retriever = Retriever(VectorStore())
        return self._retriever

    def consultar(
        self,
        pergunta: str,
        *,
        top_k: int = TOP_K_PADRAO,
        distancia_maxima: float = DISTANCIA_MAXIMA,
    ) -> ConsultaDocumental:
        """Busca trechos relevantes. Levanta ValueError para pergunta vazia ou top_k inválido."""
        pergunta = (pergunta or "").strip()
        if not pergunta:
            raise ValueError("A pergunta não pode estar vazia.")
        if not 1 <= top_k <= TOP_K_MAXIMO:
            raise ValueError(f"top_k deve estar entre 1 e {TOP_K_MAXIMO}.")

        encontrados = self._obter_retriever().retrieve(
            pergunta, top_k=top_k, max_distance=distancia_maxima
        )

        trechos = [
            TrechoDocumento(
                id=c.id,
                content=c.content,
                source=str(c.metadata.get("source", "desconhecido")),
                document_type=c.metadata.get("document_type"),
                page=_pagina_citavel(str(c.metadata.get("source", "")), c.metadata.get("page")),
                score=round(c.score, 4),
            )
            for c in encontrados
        ]

        fontes: list[FonteCitavel] = []
        for t in trechos:
            fonte = FonteCitavel(source=t.source, page=t.page)
            if fonte not in fontes:
                fontes.append(fonte)

        logger.info("Consulta documental: %d trecho(s) acima do limiar", len(trechos))
        if not trechos:
            return ConsultaDocumental(
                pergunta=pergunta,
                evidencia_suficiente=False,
                mensagem=(
                    "Nenhum trecho dos documentos indexados é suficientemente próximo da pergunta "
                    "(ou o índice ainda não foi construído)."
                ),
            )
        return ConsultaDocumental(
            pergunta=pergunta, trechos=trechos, fontes=fontes, evidencia_suficiente=True
        )
