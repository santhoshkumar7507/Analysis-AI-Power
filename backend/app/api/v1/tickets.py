"""Ticket management API endpoints with strict multi-tenant isolation."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketAssignRequest,
    TicketMessageCreateRequest,
    TicketMessageResponse,
    TicketDetailResponse,
    TicketListResponse,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_ticket(
    req: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new customer ticket within the tenant organization."""
    ticket = TicketService.create_ticket(
        db=db,
        organization_id=current_user.organization_id,
        req=req,
        actor_id=current_user.id,
    )
    return {"message": "Ticket created successfully", "id": ticket.id, "reference_number": ticket.reference_number}


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = Query(None, description="Filter by ticket status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    assigned_agent_id: Optional[str] = Query(None, description="Filter by assigned agent"),
    search: Optional[str] = Query(None, description="Search across subject, customer name/email, reference"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query tickets within current user's organization with filtering, search, and pagination."""
    return TicketService.list_tickets(
        db=db,
        organization_id=current_user.organization_id,
        status_filter=status,
        priority_filter=priority,
        category_filter=category,
        assigned_agent_id=assigned_agent_id,
        search_query=search,
        page=page,
        limit=limit,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete ticket details, timeline, and conversation history."""
    return TicketService.get_ticket(
        db=db,
        organization_id=current_user.organization_id,
        ticket_id=ticket_id,
    )


@router.patch("/{ticket_id}")
def update_ticket(
    ticket_id: str,
    req: TicketUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update ticket status, priority, or category."""
    ticket = TicketService.update_ticket(
        db=db,
        organization_id=current_user.organization_id,
        ticket_id=ticket_id,
        req=req,
        actor=current_user,
    )
    return {"message": "Ticket updated successfully", "status": ticket.status, "priority": ticket.priority}


@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    req: TicketAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign ticket to a team member or department team."""
    ticket = TicketService.assign_ticket(
        db=db,
        organization_id=current_user.organization_id,
        ticket_id=ticket_id,
        req=req,
        actor=current_user,
    )
    return {"message": "Ticket assigned successfully", "assigned_agent_id": ticket.assigned_agent_id}


@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=status.HTTP_201_CREATED)
def post_ticket_message(
    ticket_id: str,
    req: TicketMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Post a customer-visible reply or internal team note."""
    msg = TicketService.add_message(
        db=db,
        organization_id=current_user.organization_id,
        ticket_id=ticket_id,
        req=req,
        actor=current_user,
    )
    return {
        "id": msg.id,
        "ticket_id": msg.ticket_id,
        "sender_type": msg.sender_type,
        "sender_user_id": msg.sender_user_id,
        "sender_name": current_user.full_name,
        "body": msg.body,
        "is_internal_note": msg.is_internal_note,
        "created_at": msg.created_at,
    }
