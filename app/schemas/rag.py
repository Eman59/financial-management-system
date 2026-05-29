from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)
    document_type: Optional[str] = None
    company_name: Optional[str] = None


class RAGSearchResult(BaseModel):
    document_id: str
    title: str
    company_name: str
    document_type: str
    chunk_text: str
    relevance_score: float


class RAGSearchResponse(BaseModel):
    query: str
    results: List[RAGSearchResult]
    total_results: int


class RAGIndexResponse(BaseModel):
    document_id: str
    status: str
    chunks_indexed: int
    message: str


class RAGContextResponse(BaseModel):
    document_id: str
    title: str
    related_chunks: List[dict]
    related_documents: List[dict]
