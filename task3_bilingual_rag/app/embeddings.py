"""
Embedding generation and a minimal in-memory vector index.

Uses OpenAI's text-embedding-3-small model, which supports multilingual
input — meaning an Arabic query can retrieve semantically relevant
English chunks and vice versa, without needing separate per-language
indexes or translation as a pre-processing step.

The index itself is a simple in-memory list with cosine similarity
search via numpy. No external vector database is required, keeping
this fully offline-friendly aside from the embedding API calls
themselves (see app/llm.py for the offline-mock fallback path).
"""

import os
import json
import logging
import numpy as np
from openai import OpenAI

from app.loader import Chunk

logger = logging.getLogger("rag_service")

EMBEDDING_MODEL = "text-embedding-3-small"
INDEX_CACHE_PATH = os.getenv("RAG_INDEX_CACHE", "/data/embeddings_cache.json")

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def embed_text(text: str) -> list[float]:
    """Generate an embedding vector for a single piece of text."""
    client = get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single API call (cheaper, faster)."""
    client = get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


class VectorIndex:
    """A minimal in-memory vector index with cosine similarity search."""

    def __init__(self):
        self.chunks: list[Chunk] = []
        self.vectors: np.ndarray = None

    def build(self, chunks: list[Chunk], use_cache: bool = True) -> None:
        """Embed all chunks and build the index. Caches embeddings to disk to avoid
        re-embedding identical content on every restart (saves cost and latency)."""
        cached = self._load_cache() if use_cache else None

        if cached and self._cache_matches(cached, chunks):
            logger.info(f"Loaded {len(chunks)} chunk embeddings from cache.")
            self.chunks = chunks
            self.vectors = np.array(cached["vectors"])
            return

        logger.info(f"Embedding {len(chunks)} chunks via {EMBEDDING_MODEL}...")
        texts = [c.text for c in chunks]
        vectors = embed_batch(texts)

        self.chunks = chunks
        self.vectors = np.array(vectors)
        self._save_cache(chunks, vectors)
        logger.info(f"Index built with {len(chunks)} chunks.")

    def search(self, query_vector: list[float], top_k: int = 3) -> list[tuple[Chunk, float]]:
        """Return the top_k most similar chunks to the query, with their similarity scores."""
        if self.vectors is None or len(self.chunks) == 0:
            return []

        query_arr = np.array(query_vector)
        query_norm = query_arr / np.linalg.norm(query_arr)
        index_norms = self.vectors / np.linalg.norm(self.vectors, axis=1, keepdims=True)

        similarities = index_norms @ query_norm
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(self.chunks[i], float(similarities[i])) for i in top_indices]

    def _load_cache(self) -> dict | None:
        if not os.path.exists(INDEX_CACHE_PATH):
            return None
        try:
            with open(INDEX_CACHE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_cache(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        os.makedirs(os.path.dirname(INDEX_CACHE_PATH), exist_ok=True)
        cache_data = {
            "chunk_ids": [c.chunk_id for c in chunks],
            "vectors": vectors,
        }
        with open(INDEX_CACHE_PATH, "w") as f:
            json.dump(cache_data, f)

    def _cache_matches(self, cached: dict, chunks: list[Chunk]) -> bool:
        """Check the cache was built from the exact same set of chunks (by ID)."""
        cached_ids = set(cached.get("chunk_ids", []))
        current_ids = {c.chunk_id for c in chunks}
        return cached_ids == current_ids
