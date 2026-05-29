from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DocumentUpload(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company_name: str = Field(..., min_length=1, max_length=200)
    document_type: str = Field(..., pattern="^(invoice|report|contract)$")


class DocumentResponse(BaseModel):
    id: str
    title: str
    company_name: str
    document_type: str
    uploaded_by: str
    created_at: datetime
    is_indexed: str

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    file_path: str
    content: Optional[str] = None


class DocumentSearchQuery(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    document_type: Optional[str] = None
    uploaded_by: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
