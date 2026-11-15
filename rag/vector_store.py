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

"""Armazenamento vetorial dos documentos do Sabor da Terra."""

import hashlib
import json

import chromadb
from google import genai
from google.genai import types

from rag.chunker import DocumentChunk
from utils.config import get_settings


class VectorStore:
    """Gerencia o armazenamento e a recuperação de vetores no ChromaDB."""

    EMBEDDING_MODEL = "gemini-embedding-001"

    def __init__(
        self,
        collection_name: str = "sabor_da_terra",
    ) -> None:
        """Inicializa o banco vetorial local e sua coleção."""

        settings = get_settings()

        self.client = chromadb.PersistentClient(
            path=str(settings.vector_store_path)
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._embedding_client = None

    def _get_embedding_client(self) -> genai.Client:
        """Inicializa o cliente Gemini quando necessário."""

        if self._embedding_client is None:
            settings = get_settings()

            if settings.google_api_key is None:
                raise ValueError(
                    "GOOGLE_API_KEY não está configurada."
                )

            api_key = settings.google_api_key.get_secret_value()

            self._embedding_client = genai.Client(
                api_key=api_key
            )

        return self._embedding_client

    def _generate_embeddings(
        self,
        texts: list[str],
        task_type: str,
    ) -> list[list[float]]:
        """Gera embeddings para uma lista de textos."""

        if not texts:
            return []

        client = self._get_embedding_client()

        response = client.models.embed_content(
            model=self.EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
            ),
        )

        if not response.embeddings:
            raise ValueError(
                "O Gemini não retornou embeddings."
            )

        if len(response.embeddings) != len(texts):
            raise ValueError(
                "A quantidade de embeddings retornados "
                "é diferente da quantidade de textos enviados."
            )

        return [
            embedding.values
            for embedding in response.embeddings
        ]

    def _generate_chunk_id(self, chunk: DocumentChunk) -> str:
        """Gera um identificador estável para cada chunk."""

        identity = {
            "source": chunk.metadata["source"],
            "page": chunk.metadata.get("page"),
            "chunk_index": chunk.metadata["chunk_index"],
        }

        content = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
        )

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    def _prepare_metadata(self, metadata: dict) -> dict:
        """Converte metadados para formatos aceitos pelo ChromaDB."""

        prepared = {}

        for key, value in metadata.items():
            if value is None:
                continue

            if isinstance(value, (str, int, float, bool)):
                prepared[key] = value

            elif isinstance(value, (dict, list, tuple)):
                prepared[key] = json.dumps(
                    value,
                    ensure_ascii=False,
                )

            else:
                raise TypeError(
                    f"Tipo de metadado não suportado: {key}"
                )

        return prepared

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Gera embeddings e armazena chunks no ChromaDB."""

        if not chunks:
            return

        for chunk in chunks:
            if not chunk.text.strip():
                raise ValueError(
                    "Não é possível armazenar um chunk vazio."
                )

            if "source" not in chunk.metadata:
                raise ValueError(
                    "O chunk precisa possuir o metadado 'source'."
                )

            if "chunk_index" not in chunk.metadata:
                raise ValueError(
                    "O chunk precisa possuir o metadado 'chunk_index'."
                )

        texts = [chunk.text for chunk in chunks]

        embeddings = self._generate_embeddings(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
        )

        ids = [
            self._generate_chunk_id(chunk)
            for chunk in chunks
        ]

        metadatas = [
            self._prepare_metadata(chunk.metadata)
            for chunk in chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def replace_document(
        self,
        source: str,
        chunks: list[DocumentChunk],
    ) -> None:
        """Substitui os chunks de um documento sem apagar os antigos antecipadamente."""

        if not source.strip():
            raise ValueError(
                "A origem do documento não pode estar vazia."
            )

        chunk_ids = set()

        for chunk in chunks:
            if not chunk.text.strip():
                raise ValueError(
                    "Não é possível armazenar um chunk vazio."
                )

            if chunk.metadata.get("source") != source:
                raise ValueError(
                    "Todos os chunks devem pertencer ao documento informado."
                )

            chunk_index = chunk.metadata.get("chunk_index")

            if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index <= 0:
                raise ValueError(
                    "chunk_index deve ser um inteiro positivo."
                )

            chunk_id = self._generate_chunk_id(chunk)

            if chunk_id in chunk_ids:
                raise ValueError(
                    "Existem chunks com identificadores duplicados."
                )

            chunk_ids.add(chunk_id)

        if not chunks:
            raise ValueError(
                "Não é possível substituir um documento sem chunks."
            )

        texts = [chunk.text for chunk in chunks]

        embeddings = self._generate_embeddings(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
        )

        ids = [
            self._generate_chunk_id(chunk)
            for chunk in chunks
        ]

        metadatas = [
            self._prepare_metadata(chunk.metadata)
            for chunk in chunks
        ]

        new_ids = set(ids)

        existing = self.collection.get(
            where={"source": source},
            include=[],
        )

        obsolete_ids = [
            chunk_id
            for chunk_id in existing["ids"]
            if chunk_id not in new_ids
        ]

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        if obsolete_ids:
            self.collection.delete(ids=obsolete_ids)

    def search(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        """Busca os chunks mais relevantes para uma consulta."""

        if not query.strip():
            raise ValueError(
                "A consulta não pode estar vazia."
            )

        if n_results <= 0:
            raise ValueError(
                "n_results deve ser maior que zero."
            )

        collection_count = self.collection.count()

        if collection_count == 0:
            return []

        query_embedding = self._generate_embeddings(
            [query],
            task_type="RETRIEVAL_QUERY",
        )

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, collection_count),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for text, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            chunk = DocumentChunk(
                text=text,
                metadata=metadata,
            )

            chunks.append((chunk, distance))

        return chunks

    def delete_document(self, source: str) -> int:
        """Remove todos os chunks associados a um documento."""

        if not source.strip():
            raise ValueError(
                "A origem do documento não pode estar vazia."
            )

        results = self.collection.get(
            where={"source": source},
            include=[],
        )

        ids = results["ids"]

        if not ids:
            return 0

        self.collection.delete(ids=ids)

        return len(ids)
