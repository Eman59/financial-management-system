from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.rag import (
    RAGSearchRequest,
    RAGSearchResult,
    RAGSearchResponse,
    RAGIndexResponse,
    RAGContextResponse,
)
from app.services.auth_service import check_permission
from app.services.document_service import get_document_by_id
from app.services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["RAG - Semantic Search"])


@router.post("/index-document", response_model=RAGIndexResponse)
async def index_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("rag", "index")),
):
    """Generate embeddings for a document and store in vector database."""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not doc.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no extractable content",
        )

    chunks_indexed = await rag_service.index_document(doc)

    # Update document indexed status
    doc.is_indexed = "true"
    await db.flush()

    return RAGIndexResponse(
        document_id=doc.id,
        status="success",
        chunks_indexed=chunks_indexed,
        message=f"Document '{doc.title}' indexed successfully with {chunks_indexed} chunks",
    )


@router.delete("/remove-document/{document_id}")
async def remove_document_embeddings(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("rag", "index")),
):
    """Remove document embeddings from vector database."""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await rag_service.remove_document(document_id)

    doc.is_indexed = "false"
    await db.flush()

    return {
        "message": f"Embeddings removed for document '{doc.title}'",
        "document_id": document_id,
    }


@router.post("/search", response_model=RAGSearchResponse)
async def semantic_search(
    request: RAGSearchRequest,
    current_user: User = Depends(check_permission("rag", "search")),
):
    """Perform semantic search across indexed financial documents."""
    results = await rag_service.search(
        query=request.query,
        top_k=request.top_k,
        document_type=request.document_type,
        company_name=request.company_name,
    )

    search_results = [
        RAGSearchResult(
            document_id=r["document_id"],
            title=r["title"],
            company_name=r["company_name"],
            document_type=r["document_type"],
            chunk_text=r["chunk_text"],
            relevance_score=r["relevance_score"],
        )
        for r in results
    ]

    return RAGSearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )


@router.get("/context/{document_id}", response_model=RAGContextResponse)
async def get_document_context(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("rag", "search")),
):
    """Retrieve related document context and similar documents."""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    context = await rag_service.get_document_context(document_id)

    return RAGContextResponse(
        document_id=document_id,
        title=doc.title,
        related_chunks=context["chunks"],
        related_documents=context["related_documents"],
    )
