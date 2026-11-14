"""Schemas de consulta documental.

Função:
    Representa trechos recuperados, fontes e a resposta fundamentada do RAG.

Responsabilidades:
    - Fonte: arquivo de origem, tipo do documento e página
    - Trecho recuperado com score de similaridade
    - Resposta documental com lista de fontes ou indicação de evidência insuficiente

Não deve:
    - Conter lógica de busca

Relações:
    Usa:        pydantic
    Usado por:  rag.retriever, services.documento_service

Observação:
    Arquivo adicionado à estrutura original: o enunciado exige citar a fonte de cada resposta.

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
