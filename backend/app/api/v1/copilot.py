"""AI Ticket Intelligence and Copilot Reply Approval API endpoints."""

import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket, TicketMessage, MessageSenderType, TicketStatus
from app.models.ai import AIAnalysisRun, AIReplyDraft
from app.ai.copilot import AICopilotEngine
from app.services.knowledge_service import KnowledgeService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/tickets", tags=["AI Copilot & Intelligence"])


class ApproveDraftRequest(BaseModel):
    edited_reply: Optional[str] = None
    review_comment: Optional[str] = None


class RejectDraftRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=2)


@router.get("/{ticket_id}/ai-analysis")
def get_or_run_ai_analysis(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve existing AI ticket classification or trigger asynchronous analysis."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.organization_id == current_user.organization_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    # Check for existing run
    run = (
        db.query(AIAnalysisRun)
        .filter(AIAnalysisRun.ticket_id == ticket.id)
        .order_by(AIAnalysisRun.created_at.desc())
        .first()
    )

    if not run:
        # Run classification
        analysis = AICopilotEngine.classify_ticket(ticket.subject, ticket.description)
        run = AIAnalysisRun(
            ticket_id=ticket.id,
            category=analysis["category"],
            priority=analysis["priority"],
            sentiment=analysis["sentiment"],
            issue_summary=analysis["issue_summary"],
            detected_language="en",
            suggested_team_name=analysis["suggested_team_name"],
            recommended_action=analysis["recommended_action"],
            confidence_score=analysis["confidence_score"],
            model_provider=analysis.get("model_provider", "mock"),
            latency_ms=analysis.get("latency_ms", 0),
            status=analysis.get("status", "success"),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

    return {
        "id": run.id,
        "ticket_id": run.ticket_id,
        "category": run.category,
        "priority": run.priority,
        "sentiment": run.sentiment,
        "issue_summary": run.issue_summary,
        "suggested_team_name": run.suggested_team_name,
        "recommended_action": run.recommended_action,
        "confidence_score": run.confidence_score,
        "model_provider": run.model_provider,
        "latency_ms": run.latency_ms,
        "status": run.status,
    }


@router.post("/{ticket_id}/copilot/generate")
def generate_copilot_draft(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Perform grounded RAG vector retrieval and synthesize an AI reply draft with citations."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.organization_id == current_user.organization_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    # Retrieve relevant knowledge base chunks
    query = f"{ticket.subject} {ticket.description}"
    retrieved_chunks = KnowledgeService.semantic_search(
        db=db,
        organization_id=current_user.organization_id,
        query=query,
        top_k=3,
        threshold=0.35,
    )

    # Synthesize grounded draft
    draft_data = AICopilotEngine.generate_reply_draft(
        subject=ticket.subject,
        description=ticket.description,
        retrieved_chunks=retrieved_chunks,
    )

    draft = AIReplyDraft(
        ticket_id=ticket.id,
        suggested_reply=draft_data["suggested_reply"],
        reasoning=draft_data["reasoning"],
        citations_json=json.dumps(draft_data.get("citations", [])),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        "id": draft.id,
        "ticket_id": draft.ticket_id,
        "suggested_reply": draft.suggested_reply,
        "reasoning": draft.reasoning,
        "citations": draft_data.get("citations", []),
        "is_grounded": draft_data.get("is_grounded", False),
        "status": draft.status,
    }


@router.get("/{ticket_id}/copilot/draft")
def get_active_copilot_draft(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch the latest AI reply draft for a ticket."""
    draft = (
        db.query(AIReplyDraft)
        .filter(AIReplyDraft.ticket_id == ticket_id)
        .order_by(AIReplyDraft.created_at.desc())
        .first()
    )
    if not draft:
        return {"draft": None}

    citations = json.loads(draft.citations_json) if draft.citations_json else []
    return {
        "draft": {
            "id": draft.id,
            "ticket_id": draft.ticket_id,
            "suggested_reply": draft.suggested_reply,
            "reasoning": draft.reasoning,
            "citations": citations,
            "status": draft.status,
            "final_sent_body": draft.final_sent_body,
        }
    }


@router.post("/{ticket_id}/copilot/approve")
def approve_copilot_draft(
    ticket_id: str,
    req: ApproveDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Human approval workflow: Approves draft (or edits), posts it as an agent reply, and logs audit record."""
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.organization_id == current_user.organization_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    draft = (
        db.query(AIReplyDraft)
        .filter(AIReplyDraft.ticket_id == ticket.id, AIReplyDraft.status == "draft")
        .order_by(AIReplyDraft.created_at.desc())
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active draft awaiting review.")

    final_body = req.edited_reply.strip() if req.edited_reply else draft.suggested_reply
    was_edited = req.edited_reply is not None and req.edited_reply.strip() != draft.suggested_reply

    draft.status = "edited_and_approved" if was_edited else "approved"
    draft.reviewer_id = current_user.id
    draft.review_comment = req.review_comment
    draft.final_sent_body = final_body

    # Append to ticket messages as customer-visible agent reply
    message = TicketMessage(
        ticket_id=ticket.id,
        sender_type=MessageSenderType.AGENT,
        sender_user_id=current_user.id,
        body=final_body,
        is_internal_note=False,
    )
    db.add(message)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    if not ticket.first_responded_at:
        ticket.first_responded_at = now
    ticket.updated_at = now

    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS


    AuditService.log_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="copilot.draft_approved",
        entity_type="ai_reply_draft",
        entity_id=draft.id,
        details={"was_edited": was_edited, "ticket_id": ticket.id},
    )

    db.commit()
    return {"message": "AI reply draft approved and dispatched to customer thread", "status": draft.status}


@router.post("/{ticket_id}/copilot/reject")
def reject_copilot_draft(
    ticket_id: str,
    req: RejectDraftRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reject AI draft with feedback rationale."""
    draft = (
        db.query(AIReplyDraft)
        .filter(AIReplyDraft.ticket_id == ticket_id, AIReplyDraft.status == "draft")
        .order_by(AIReplyDraft.created_at.desc())
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active draft to reject.")

    draft.status = "rejected"
    draft.reviewer_id = current_user.id
    draft.review_comment = req.rejection_reason

    AuditService.log_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="copilot.draft_rejected",
        entity_type="ai_reply_draft",
        entity_id=draft.id,
        details={"reason": req.rejection_reason},
    )

    db.commit()
    return {"message": "AI draft rejected", "status": "rejected"}
