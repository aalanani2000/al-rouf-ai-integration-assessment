from pydantic import BaseModel, Field
from typing import List


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What is the warranty period for high bay lights?"])
    top_k: int = Field(default=3, ge=1, le=10, description="Number of chunks to retrieve")


class SourceMatch(BaseModel):
    source_doc: str
    similarity_score: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    cited_sources: List[str]
    confidence: str
    refused: bool
    retrieved_matches: List[SourceMatch]
    latency_seconds: float
    estimated_cost_usd: float
