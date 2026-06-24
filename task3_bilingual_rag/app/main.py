"""
AL ROUF LED Lighting — Bilingual RAG Knowledge Service

Answers questions in English or Arabic using retrieval over a small
set of sample product/policy documents. Refuses clearly when the
question falls outside the supported document scope rather than
letting the model improvise an answer.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from app.loader import load_and_chunk_all
from app.embeddings import VectorIndex, embed_text
from app.llm import generate_answer
from app.schemas import QueryRequest, QueryResponse, SourceMatch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag_service")

_index = VectorIndex()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading and chunking documents...")
    chunks = load_and_chunk_all()
    logger.info(f"Loaded {len(chunks)} chunks from documents directory.")
    _index.build(chunks)
    logger.info("RAG service ready.")
    yield


app = FastAPI(
    title="AL ROUF Bilingual RAG Knowledge Service",
    description=(
        "Answers English/Arabic questions over a small set of product "
        "and policy documents, with citations and explicit refusal "
        "when a question falls outside the supported scope."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "indexed_chunks": len(_index.chunks)}


@app.get("/documents", tags=["System"])
def list_documents():
    """List the source documents currently indexed."""
    sources = sorted(set(c.source_doc for c in _index.chunks))
    return {"documents": sources, "total_chunks": len(_index.chunks)}


@app.post("/ask", response_model=QueryResponse, tags=["RAG"])
def ask_question(request: QueryRequest):
    """
    Ask a question in English or Arabic. Retrieves relevant document
    chunks and generates a cited answer, or refuses explicitly if the
    question is outside the supported document scope.
    """
    try:
        query_vector = embed_text(request.question)
    except Exception as e:
        logger.exception(f"Embedding failed for query: {e}")
        raise HTTPException(status_code=502, detail="Embedding service unavailable.")

    matches = _index.search(query_vector, top_k=request.top_k)
    result = generate_answer(request.question, matches)

    return {
        "question": request.question,
        "answer": result["answer"],
        "cited_sources": result["cited_sources"],
        "confidence": result["confidence"],
        "refused": result["refused"],
        "retrieved_matches": [
            SourceMatch(source_doc=chunk.source_doc, similarity_score=round(score, 4))
            for chunk, score in matches
        ],
        "latency_seconds": result["latency_seconds"],
        "estimated_cost_usd": result["estimated_cost_usd"],
    }
