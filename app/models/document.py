from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum

from app.database import Base


class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    REPORT = "report"
    CONTRACT = "contract"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    document_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_indexed = Column(String, default="false")

    owner = relationship("User", back_populates="documents")
