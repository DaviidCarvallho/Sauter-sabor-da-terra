"""Banco vetorial.

Função:
    Único módulo que conhece o ChromaDB e a geração de embeddings.

Responsabilidades:
    - Persistir o índice em VECTOR_STORE_DIR
    - Gerar embeddings (modelo ainda a decidir) e gravar os trechos
    - Consultar por similaridade

Não deve:
    - Vazar detalhes do ChromaDB para outras camadas

Relações:
    Usa:        chromadb, utils.config
    Usado por:  rag.ingestion, rag.retriever

Observação:
    O índice é um artefato derivado: pode ser reconstruído pela ingestão. O GCS guarda os arquivos, não o índice.

Status: esqueleto. Será implementado na Fase 5 (RAG e Agente de Documentos).
"""
