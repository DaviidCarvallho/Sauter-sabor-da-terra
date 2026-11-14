"""Testes da consulta documental (RAG).

Casos previstos (Fase 5 (RAG e Agente de Documentos)):
- Toda resposta cita o arquivo de origem
- Pergunta sem evidência nos documentos retorna 'não encontrei', sem inventar
- Certificação orgânica vigente para mel é localizada na base
- Rastreabilidade de um lote combina lotes.csv e documentos
"""

import pytest

pytestmark = pytest.mark.skip(reason="Esqueleto: implementar junto com a Fase 5 (RAG e Agente de Documentos)")


def test_pendente():
    ...
