"""Knowledge Base and Vector Retrieval service with multi-tenant isolation and hybrid search."""

import os
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.knowledge import KnowledgeDocument, DocumentChunk, DocumentStatus
from app.services.chunking import ChunkingEngine
from app.ai.embeddings import EmbeddingEngine
from app.services.audit_service import AuditService

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md", "json"}


class KnowledgeService:
    @classmethod
    def upload_and_index(
        cls,
        db: Session,
        organization_id: str,
        file: UploadFile,
        title: str,
        actor_id: Optional[str] = None,
    ) -> KnowledgeDocument:
        """Validate, store, extract, chunk, and embed an uploaded knowledge document."""
        # Validate extension
        filename = file.filename or "uploaded_document"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        # Secure file storage path
        org_storage_dir = os.path.join(settings.STORAGE_DIR, organization_id)
        os.makedirs(org_storage_dir, exist_ok=True)

        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}.{ext}"
        target_path = os.path.join(org_storage_dir, safe_filename)

        # Read content and enforce size limits
        content = file.file.read()
        file_size = len(content)
        if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
            )

        with open(target_path, "wb") as f:
            f.write(content)

        # Create KnowledgeDocument record in PENDING state
        doc = KnowledgeDocument(
            organization_id=organization_id,
            title=title.strip() or filename,
            file_type=ext,
            file_path=target_path,
            file_size=file_size,
            status=DocumentStatus.INDEXING,
        )
        db.add(doc)
        db.flush()

        try:
            # Chunk document
            chunks_data = ChunkingEngine.chunk_document(
                file_path=target_path,
                file_type=ext,
                max_chunk_size=800,
                chunk_overlap=100,
            )

            # Generate embeddings and persist chunks
            for chunk_dict in chunks_data:
                chunk_text = chunk_dict["content"]
                embedding = EmbeddingEngine.get_embedding(chunk_text)

                doc_chunk = DocumentChunk(
                    document_id=doc.id,
                    organization_id=organization_id,
                    chunk_index=chunk_dict["chunk_index"],
                    content=chunk_text,
                    metadata_json=json.dumps(chunk_dict.get("metadata", {})),
                    embedding_json=json.dumps(embedding),
                )
                db.add(doc_chunk)

            doc.chunk_count = len(chunks_data)
            doc.status = DocumentStatus.INDEXED
            doc.updated_at = datetime.now(timezone.utc)

            AuditService.log_event(
                db=db,
                organization_id=organization_id,
                actor_id=actor_id,
                action="knowledge.document_indexed",
                entity_type="knowledge_document",
                entity_id=doc.id,
                details={"title": doc.title, "chunk_count": doc.chunk_count},
            )

            db.commit()
            db.refresh(doc)
            return doc

        except Exception as e:
            db.rollback()
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract and index document: {str(e)}",
            )

    @staticmethod
    def list_documents(db: Session, organization_id: str) -> List[KnowledgeDocument]:
        """List all indexed documents strictly within the tenant boundary."""
        return (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.organization_id == organization_id)
            .order_by(KnowledgeDocument.created_at.desc())
            .all()
        )

    @staticmethod
    def get_document_chunks(db: Session, organization_id: str, document_id: str) -> List[DocumentChunk]:
        """Retrieve chunks for a document verifying tenant ownership."""
        doc = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.id == document_id, KnowledgeDocument.organization_id == organization_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        return (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id, DocumentChunk.organization_id == organization_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

    @staticmethod
    def delete_document(db: Session, organization_id: str, document_id: str, actor_id: Optional[str] = None) -> bool:
        """Delete document file and remove all indexed vector chunks."""
        doc = (
            db.query(KnowledgeDocument)
            .filter(KnowledgeDocument.id == document_id, KnowledgeDocument.organization_id == organization_id)
            .first()
        )
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        # Remove physical file if exists
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

        AuditService.log_event(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="knowledge.document_deleted",
            entity_type="knowledge_document",
            entity_id=doc.id,
            details={"title": doc.title},
        )

        db.delete(doc)
        db.commit()
        return True

    @classmethod
    def semantic_search(
        cls,
        db: Session,
        organization_id: str,
        query: str,
        top_k: int = 5,
        threshold: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """Hybrid vector retrieval strictly constrained to the organization tenant boundary."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        query_embedding = EmbeddingEngine.get_embedding(cleaned_query)

        # Query all chunks belonging strictly to this organization
        chunks = (
            db.query(DocumentChunk, KnowledgeDocument.title)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .filter(DocumentChunk.organization_id == organization_id)
            .all()
        )

        scored_results = []
        query_words = set(cleaned_query.lower().split())

        for chunk, doc_title in chunks:
            chunk_embedding = json.loads(chunk.embedding_json)
            sim_score = EmbeddingEngine.cosine_similarity(query_embedding, chunk_embedding)

            # Keyword lexical matching bonus (hybrid search)
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            keyword_boost = min(0.15, overlap * 0.03)
            final_score = round(min(1.0, sim_score + keyword_boost), 4)

            if final_score >= threshold:
                meta = json.loads(chunk.metadata_json) if chunk.metadata_json else {}
                section = meta.get("section", f"Chunk #{chunk.chunk_index}")
                page = meta.get("page", 1)

                citation = f"[{doc_title} | Section: {section} (p. {page})]"

                scored_results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_title": doc_title,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": meta,
                    "similarity_score": final_score,
                    "citation": citation,
                })

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_results[:top_k]
