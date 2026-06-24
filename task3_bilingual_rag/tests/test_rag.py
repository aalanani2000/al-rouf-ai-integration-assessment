"""
Test suite for the bilingual RAG pipeline.

Tests are split into two groups:
1. Pure logic tests (loader, chunking) — run with no API key, no network.
2. Integration tests (embeddings, generation, full /ask flow) — require
   a real OPENAI_API_KEY and are skipped automatically if one isn't set,
   so the test suite still runs cleanly in offline/CI environments
   without failing on missing credentials.
"""

import os
import pytest
from app.loader import load_and_chunk_all, chunk_document, Chunk

REQUIRES_API_KEY = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY for embedding/generation calls",
)


# ── Loader / chunking tests (no API key needed) ──────────────────────────

def test_load_and_chunk_all_returns_chunks():
    chunks = load_and_chunk_all()
    assert len(chunks) > 0


def test_all_four_sample_documents_are_loaded():
    chunks = load_and_chunk_all()
    sources = set(c.source_doc for c in chunks)
    assert len(sources) == 4


def test_chunks_have_required_fields():
    chunks = load_and_chunk_all()
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.source_doc
        assert chunk.text.strip() != ""


def test_chunk_document_splits_on_section_headers():
    sample = "# Title\n\nIntro text.\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B."
    chunks = chunk_document("sample.md", sample, max_chunk_chars=800)
    assert len(chunks) >= 2
    assert any("Section A" in c.text for c in chunks)
    assert any("Section B" in c.text for c in chunks)


def test_chunk_document_splits_long_sections_further():
    long_para = "Word " * 500  # forces a section over max_chunk_chars
    sample = f"## Long Section\n\n{long_para}"
    chunks = chunk_document("sample.md", sample, max_chunk_chars=200)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 250  # some tolerance for paragraph boundaries


def test_arabic_document_chunks_correctly():
    """Confirms chunking handles Arabic script documents without errors,
    since this is core to the bilingual requirement."""
    chunks = load_and_chunk_all()
    arabic_chunks = [c for c in chunks if "ar.md" in c.source_doc]
    assert len(arabic_chunks) > 0
    for c in arabic_chunks:
        assert len(c.text) > 0


# ── Vector index tests (no API key needed — uses fake vectors) ──────────

def test_vector_index_search_returns_top_k():
    from app.embeddings import VectorIndex
    import numpy as np

    index = VectorIndex()
    index.chunks = [
        Chunk(chunk_id="a", source_doc="doc_a.md", text="text a"),
        Chunk(chunk_id="b", source_doc="doc_b.md", text="text b"),
        Chunk(chunk_id="c", source_doc="doc_c.md", text="text c"),
    ]
    # Fake 2D vectors, hand-picked so similarity ordering is predictable
    index.vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])

    results = index.search(query_vector=[1.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0][0].chunk_id == "a"  # exact match should rank first


def test_vector_index_search_empty_index_returns_empty():
    from app.embeddings import VectorIndex

    index = VectorIndex()
    results = index.search(query_vector=[1.0, 0.0], top_k=3)
    assert results == []


# ── Refusal logic tests (no API key needed) ──────────────────────────────

def test_refusal_when_no_chunks_retrieved():
    from app.llm import generate_answer

    result = generate_answer("What is the capital of France?", [])
    assert result["refused"] is True
    assert result["cited_sources"] == []
    assert result["estimated_cost_usd"] == 0.0


def test_refusal_below_similarity_threshold():
    from app.llm import generate_answer
    from app.loader import Chunk

    low_score_chunk = (Chunk(chunk_id="x", source_doc="doc.md", text="irrelevant"), 0.05)
    result = generate_answer("Completely unrelated question", [low_score_chunk])
    assert result["refused"] is True


def test_refusal_returns_arabic_message_for_arabic_question():
    from app.llm import generate_answer

    result = generate_answer("ما هي عاصمة فرنسا؟", [])
    assert result["refused"] is True
    # Arabic script should appear in the refusal message
    assert any("\u0600" <= ch <= "\u06FF" for ch in result["answer"])


def test_refusal_returns_english_message_for_english_question():
    from app.llm import generate_answer

    result = generate_answer("What is the capital of France?", [])
    assert result["refused"] is True
    assert "don't have enough information" in result["answer"]


# ── Integration tests (require real API key) ─────────────────────────────

@REQUIRES_API_KEY
def test_full_ask_flow_with_relevant_question():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "What is the warranty period for the 150W high bay light?"})
        assert response.status_code == 200
        body = response.json()
        assert body["refused"] is False
        assert len(body["cited_sources"]) > 0
        assert "doc1_product_spec_high_bay_en.md" in body["cited_sources"]


@REQUIRES_API_KEY
def test_full_ask_flow_with_arabic_question():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "ما هي مدة الضمان على إضاءة الشوارع؟"})
        assert response.status_code == 200
        body = response.json()
        assert body["refused"] is False


@REQUIRES_API_KEY
def test_full_ask_flow_refuses_out_of_scope_question():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "What is the population of Japan?"})
        assert response.status_code == 200
        body = response.json()
        assert body["refused"] is True
