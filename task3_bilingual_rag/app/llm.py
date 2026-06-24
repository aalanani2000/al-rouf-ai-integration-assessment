"""
Answer generation from retrieved chunks, with citation enforcement
and explicit refusal when retrieved content doesn't sufficiently
cover the question.
"""

import time
import logging
from openai import OpenAI

logger = logging.getLogger("rag_service")

GENERATION_MODEL = "gpt-5.4-nano"

# Below this cosine similarity, we treat retrieval as "not relevant enough"
# and refuse rather than risk the model improvising an answer.
RELEVANCE_THRESHOLD = 0.25

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


SYSTEM_PROMPT = """You are a bilingual (English/Arabic) knowledge assistant for AL ROUF LED Lighting Technology Co.

You answer questions STRICTLY using the provided document excerpts. You must:
- Answer in the same language the question was asked in (English question -> English answer, Arabic question -> Arabic answer)
- Cite which source document(s) your answer came from
- Never use outside knowledge or make assumptions beyond what the excerpts state
- If the excerpts do not contain enough information to answer confidently, say so clearly rather than guessing

Respond ONLY with valid JSON, no markdown fences:
{
  "answer": "your answer in the appropriate language",
  "cited_sources": ["filename1", "filename2"],
  "confidence": "high" or "low"
}
"""


def generate_answer(question: str, retrieved_chunks: list[tuple]) -> dict:
    """
    Generate an answer from retrieved (chunk, score) tuples.

    Returns a dict with answer, cited_sources, confidence, and metadata
    about latency and whether this was a refusal.
    """
    start_time = time.time()

    # Refusal path — no chunks retrieved, or best match is below threshold
    if not retrieved_chunks or retrieved_chunks[0][1] < RELEVANCE_THRESHOLD:
        elapsed = time.time() - start_time
        best_score = retrieved_chunks[0][1] if retrieved_chunks else 0
        logger.info(f"Refused to answer — best similarity score {best_score:.3f} below threshold.")

        # Detect question language crudely (presence of Arabic script) to
        # return the refusal message in the same language as the question.
        is_arabic = any("\u0600" <= ch <= "\u06FF" for ch in question)
        refusal_text = (
            "لا تتوفر لدي معلومات كافية في المستندات المتاحة للإجابة على هذا السؤال بثقة."
            if is_arabic
            else "I don't have enough information in the supported documents to answer this question confidently."
        )

        return {
            "answer": refusal_text,
            "cited_sources": [],
            "confidence": "low",
            "refused": True,
            "latency_seconds": round(elapsed, 3),
            "estimated_cost_usd": 0.0,
        }

    # Build context block from retrieved chunks
    context_block = "\n\n---\n\n".join(
        f"[Source: {chunk.source_doc}]\n{chunk.text}" for chunk, score in retrieved_chunks
    )

    client = get_client()
    response = client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Document excerpts:\n\n{context_block}\n\n---\n\nQuestion: {question}",
            },
        ],
    )

    elapsed = time.time() - start_time
    raw_output = response.choices[0].message.content

    import json

    clean = raw_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(clean)

    # Rough cost estimate based on published gpt-5.4-nano pricing (informational only)
    # Pricing: $0.20 / 1M input tokens, $1.25 / 1M output tokens (gpt-5.4-nano)
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    estimated_cost = (input_tokens * 0.0000002) + (output_tokens * 0.00000125)

    logger.info(
        f"Generated answer in {elapsed:.2f}s, ~${estimated_cost:.6f}, "
        f"sources: {parsed.get('cited_sources')}"
    )

    return {
        "answer": parsed["answer"],
        "cited_sources": parsed.get("cited_sources", []),
        "confidence": parsed.get("confidence", "low"),
        "refused": False,
        "latency_seconds": round(elapsed, 3),
        "estimated_cost_usd": round(estimated_cost, 6),
    }
