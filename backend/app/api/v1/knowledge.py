"""Knowledge Base and Vector Retrieval API endpoints."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & Vector RAG"])


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: str



class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.45, ge=0.0, le=1.0)


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.SUPPORT_MANAGER])),
    db: Session = Depends(get_db),
):
    """Upload and index a knowledge base document (.pdf, .docx, .txt, .md, .json) with vector embeddings."""
    doc = KnowledgeService.upload_and_index(
        db=db,
        organization_id=current_user.organization_id,
        file=file,
        title=title,
        actor_id=current_user.id,
    )
    return {
        "message": "Document indexed successfully",
        "id": doc.id,
        "title": doc.title,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
    }


@router.get("/documents")
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all knowledge base documents in the organization tenant."""
    docs = KnowledgeService.list_documents(db=db, organization_id=current_user.organization_id)
    return [
        {
            "id": d.id,
            "title": d.title,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "error_message": d.error_message,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/documents/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Inspect text chunks and metadata for an indexed document."""
    chunks = KnowledgeService.get_document_chunks(
        db=db,
        organization_id=current_user.organization_id,
        document_id=document_id,
    )
    return [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "created_at": c.created_at.isoformat(),
        }
        for c in chunks
    ]


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.SUPPORT_MANAGER])),
    db: Session = Depends(get_db),
):
    """Delete a knowledge document and remove all associated vector embeddings."""
    KnowledgeService.delete_document(
        db=db,
        organization_id=current_user.organization_id,
        document_id=document_id,
        actor_id=current_user.id,
    )
    return {"message": "Document and associated vector chunks deleted successfully"}


@router.post("/search")
def test_vector_search(
    req: SearchQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test semantic and hybrid vector retrieval against organization knowledge chunks."""
    results = KnowledgeService.semantic_search(
        db=db,
        organization_id=current_user.organization_id,
        query=req.query,
        top_k=req.top_k,
        threshold=req.threshold,
    )
    return {"query": req.query, "total_matches": len(results), "results": results}
