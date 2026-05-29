from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os

from app.database import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentSearchQuery,
    DocumentListResponse,
)
from app.services.auth_service import check_permission
from app.services.document_service import (
    save_upload_file,
    extract_text_from_file,
    create_document,
    get_all_documents,
    get_document_by_id,
    delete_document,
    search_documents,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    company_name: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("documents", "upload")),
):
    """Upload a financial document."""
    # Validate document type
    valid_types = ["invoice", "report", "contract"]
    if document_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Must be one of: {valid_types}",
        )

    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {list(ALLOWED_EXTENSIONS)}",
        )

    # Save file
    file_path = await save_upload_file(file)

    # Extract text content
    content = await extract_text_from_file(file_path)

    # Create document record
    doc = await create_document(
        db=db,
        title=title,
        company_name=company_name,
        document_type=document_type,
        file_path=file_path,
        uploaded_by=current_user.id,
        content=content,
    )

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("documents", "read")),
):
    """Retrieve all documents (paginated)."""
    documents = await get_all_documents(db, skip=skip, limit=limit)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/search", response_model=DocumentListResponse)
async def search_documents_endpoint(
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    document_type: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("documents", "read")),
):
    """Search documents by metadata."""
    query = DocumentSearchQuery(
        title=title,
        company_name=company_name,
        document_type=document_type,
        uploaded_by=uploaded_by,
    )
    documents = await search_documents(db, query)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("documents", "read")),
):
    """Retrieve document details."""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document_endpoint(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_permission("documents", "upload")),
):
    """Delete a document (requires upload/edit permission or admin)."""
    success = await delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return {"message": "Document deleted successfully", "document_id": document_id}
