"""Ticket management business logic with multi-tenant scoping and conversation tracking."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import or_, desc, asc
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.ticket import (
    Ticket,
    TicketMessage,
    TicketStatus,
    TicketPriority,
    MessageSenderType,
)
from app.models.user import User
from app.models.team import Team
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketAssignRequest,
    TicketMessageCreateRequest,
)
from app.services.audit_service import AuditService


class TicketService:
    @staticmethod
    def _generate_reference_number(db: Session, organization_id: str) -> str:
        """Generate a human-readable, unique ticket reference e.g., RES-2026-0001."""
        current_year = datetime.now(timezone.utc).year
        prefix = f"RES-{current_year}-"

        # Count existing tickets for this prefix
        count = (
            db.query(Ticket)
            .filter(Ticket.reference_number.like(f"{prefix}%"))
            .count()
        )
        return f"{prefix}{count + 1:04d}"

    @classmethod
    def create_ticket(
        cls,
        db: Session,
        organization_id: str,
        req: TicketCreateRequest,
        actor_id: Optional[str] = None,
    ) -> Ticket:
        """Create a new support ticket and record the initial customer message."""
        now = datetime.now(timezone.utc)
        ref_num = cls._generate_reference_number(db, organization_id)

        # Default SLA deadlines based on priority
        sla_hours = {
            TicketPriority.CRITICAL: (1, 4),    # (first_response_hours, resolution_hours)
            TicketPriority.HIGH: (2, 8),
            TicketPriority.MEDIUM: (4, 24),
            TicketPriority.LOW: (8, 48),
        }.get(req.priority, (4, 24))

        first_resp_deadline = now + timedelta(hours=sla_hours[0])
        resolution_deadline = now + timedelta(hours=sla_hours[1])

        ticket = Ticket(
            organization_id=organization_id,
            reference_number=ref_num,
            customer_name=req.customer_name,
            customer_email=req.customer_email.lower(),
            subject=req.subject,
            description=req.description,
            category=req.category,
            priority=req.priority,
            status=TicketStatus.OPEN,
            channel=req.channel,
            first_response_deadline=first_resp_deadline,
            resolution_deadline=resolution_deadline,
        )
        db.add(ticket)
        db.flush()

        # Record initial customer inquiry as the first message in the thread
        initial_message = TicketMessage(
            ticket_id=ticket.id,
            sender_type=MessageSenderType.CUSTOMER,
            body=req.description,
            is_internal_note=False,
            created_at=now,
        )
        db.add(initial_message)

        AuditService.log_event(
            db=db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="ticket.created",
            entity_type="ticket",
            entity_id=ticket.id,
            details={
                "reference_number": ticket.reference_number,
                "category": ticket.category,
                "priority": ticket.priority,
            },
        )

        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def list_tickets(
        db: Session,
        organization_id: str,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """List tickets strictly scoped to the tenant organization with flexible filters."""
        query = db.query(Ticket).filter(Ticket.organization_id == organization_id)

        if status_filter:
            query = query.filter(Ticket.status == status_filter)
        if priority_filter:
            query = query.filter(Ticket.priority == priority_filter)
        if category_filter:
            query = query.filter(Ticket.category == category_filter)
        if assigned_agent_id:
            query = query.filter(Ticket.assigned_agent_id == assigned_agent_id)

        if search_query:
            pattern = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Ticket.reference_number.ilike(pattern),
                    Ticket.subject.ilike(pattern),
                    Ticket.customer_name.ilike(pattern),
                    Ticket.customer_email.ilike(pattern),
                )
            )

        total = query.count()
        total_pages = max(1, (total + limit - 1) // limit)
        offset = (page - 1) * limit

        tickets = (
            query.order_by(desc(Ticket.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Enrich items with agent and team names
        items = []
        for t in tickets:
            items.append({
                "id": t.id,
                "reference_number": t.reference_number,
                "customer_name": t.customer_name,
                "customer_email": t.customer_email,
                "subject": t.subject,
                "category": t.category,
                "priority": t.priority,
                "status": t.status,
                "channel": t.channel,
                "assigned_agent_name": t.assigned_agent.full_name if t.assigned_agent else None,
                "assigned_team_name": t.assigned_team.name if t.assigned_team else None,
                "first_response_deadline": t.first_response_deadline,
                "resolution_deadline": t.resolution_deadline,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }

    @staticmethod
    def get_ticket(db: Session, organization_id: str, ticket_id: str) -> dict:
        """Retrieve ticket details with tenant boundary verification."""
        ticket = (
            db.query(Ticket)
            .filter(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

        # Build message history with sender names
        messages_data = []
        for m in ticket.messages:
            sender_name = "Customer"
            if m.sender_type == MessageSenderType.AGENT and m.sender_user:
                sender_name = m.sender_user.full_name
            elif m.sender_type == MessageSenderType.AI_COPILOT:
                sender_name = "ResolveAI Copilot"
            elif m.sender_type == MessageSenderType.SYSTEM:
                sender_name = "System"

            messages_data.append({
                "id": m.id,
                "ticket_id": m.ticket_id,
                "sender_type": m.sender_type,
                "sender_user_id": m.sender_user_id,
                "sender_name": sender_name,
                "body": m.body,
                "is_internal_note": m.is_internal_note,
                "created_at": m.created_at,
            })

        return {
            "id": ticket.id,
            "reference_number": ticket.reference_number,
            "customer_name": ticket.customer_name,
            "customer_email": ticket.customer_email,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "channel": ticket.channel,
            "assigned_agent_id": ticket.assigned_agent_id,
            "assigned_agent_name": ticket.assigned_agent.full_name if ticket.assigned_agent else None,
            "assigned_team_id": ticket.assigned_team_id,
            "assigned_team_name": ticket.assigned_team.name if ticket.assigned_team else None,
            "first_response_deadline": ticket.first_response_deadline,
            "resolution_deadline": ticket.resolution_deadline,
            "first_responded_at": ticket.first_responded_at,
            "resolved_at": ticket.resolved_at,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "messages": messages_data,
            "attachments": [
                {
                    "id": a.id,
                    "ticket_id": a.ticket_id,
                    "file_name": a.file_name,
                    "file_size": a.file_size,
                    "content_type": a.content_type,
                    "created_at": a.created_at,
                }
                for a in ticket.attachments
            ],
        }

    @staticmethod
    def update_ticket(
        db: Session,
        organization_id: str,
        ticket_id: str,
        req: TicketUpdateRequest,
        actor: User,
    ) -> Ticket:
        """Update ticket status, priority, or category with audit logging and timestamp updates."""
        ticket = (
            db.query(Ticket)
            .filter(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

        changes = {}
        now = datetime.now(timezone.utc)

        if req.status and req.status != ticket.status:
            changes["status"] = {"old": ticket.status, "new": req.status}
            ticket.status = req.status
            if req.status == TicketStatus.RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = now
            elif req.status == TicketStatus.CLOSED and not ticket.closed_at:
                ticket.closed_at = now

        if req.priority and req.priority != ticket.priority:
            changes["priority"] = {"old": ticket.priority, "new": req.priority}
            ticket.priority = req.priority

        if req.category and req.category != ticket.category:
            changes["category"] = {"old": ticket.category, "new": req.category}
            ticket.category = req.category

        if changes:
            ticket.updated_at = now
            AuditService.log_event(
                db=db,
                organization_id=organization_id,
                actor_id=actor.id,
                action="ticket.updated",
                entity_type="ticket",
                entity_id=ticket.id,
                details=changes,
            )
            db.commit()
            db.refresh(ticket)

        return ticket

    @staticmethod
    def assign_ticket(
        db: Session,
        organization_id: str,
        ticket_id: str,
        req: TicketAssignRequest,
        actor: User,
    ) -> Ticket:
        """Assign ticket to a designated support agent or department team."""
        ticket = (
            db.query(Ticket)
            .filter(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

        # Validate agent belongs to organization
        if req.assigned_agent_id:
            agent = (
                db.query(User)
                .filter(User.id == req.assigned_agent_id, User.organization_id == organization_id)
                .first()
            )
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned agent does not exist in this organization.",
                )
            ticket.assigned_agent_id = agent.id

        if req.assigned_team_id:
            team = (
                db.query(Team)
                .filter(Team.id == req.assigned_team_id, Team.organization_id == organization_id)
                .first()
            )
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assigned team does not exist in this organization.",
                )
            ticket.assigned_team_id = team.id

        AuditService.log_event(
            db=db,
            organization_id=organization_id,
            actor_id=actor.id,
            action="ticket.assigned",
            entity_type="ticket",
            entity_id=ticket.id,
            details={
                "assigned_agent_id": ticket.assigned_agent_id,
                "assigned_team_id": ticket.assigned_team_id,
            },
        )

        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def add_message(
        db: Session,
        organization_id: str,
        ticket_id: str,
        req: TicketMessageCreateRequest,
        actor: User,
    ) -> TicketMessage:
        """Append a reply or internal note to a ticket thread."""
        ticket = (
            db.query(Ticket)
            .filter(Ticket.id == ticket_id, Ticket.organization_id == organization_id)
            .first()
        )
        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found.",
            )

        now = datetime.now(timezone.utc)

        # If an agent sends a customer-visible reply for the first time, record first_responded_at
        if not req.is_internal_note and not ticket.first_responded_at:
            ticket.first_responded_at = now
            # Automatically transition open ticket to in_progress if open
            if ticket.status == TicketStatus.OPEN:
                ticket.status = TicketStatus.IN_PROGRESS

        message = TicketMessage(
            ticket_id=ticket.id,
            sender_type=MessageSenderType.AGENT,
            sender_user_id=actor.id,
            body=req.body,
            is_internal_note=req.is_internal_note,
            created_at=now,
        )
        db.add(message)
        ticket.updated_at = now

        AuditService.log_event(
            db=db,
            organization_id=organization_id,
            actor_id=actor.id,
            action="ticket.internal_note_added" if req.is_internal_note else "ticket.reply_sent",
            entity_type="ticket_message",
            entity_id=message.id,
            details={"ticket_id": ticket.id, "is_internal_note": req.is_internal_note},
        )

        db.commit()
        db.refresh(message)
        return message
