"""SLA Policy management, deadline monitoring, and idempotent escalation engine."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.sla import SLAPolicy, SLAEvent, Notification
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.models.user import User, UserRole
from app.services.audit_service import AuditService


class SLAService:
    @classmethod
    def get_or_create_default_policies(cls, db: Session, organization_id: str) -> List[SLAPolicy]:
        """Ensure standard enterprise SLA policies exist for the tenant."""
        existing = (
            db.query(SLAPolicy)
            .filter(SLAPolicy.organization_id == organization_id)
            .all()
        )
        if existing:
            return existing

        defaults = [
            {"priority": TicketPriority.CRITICAL, "first_response_minutes": 60, "resolution_minutes": 240},
            {"priority": TicketPriority.HIGH, "first_response_minutes": 120, "resolution_minutes": 480},
            {"priority": TicketPriority.MEDIUM, "first_response_minutes": 240, "resolution_minutes": 1440},
            {"priority": TicketPriority.LOW, "first_response_minutes": 480, "resolution_minutes": 2880},
        ]

        created = []
        for d in defaults:
            p = SLAPolicy(
                organization_id=organization_id,
                priority=d["priority"],
                first_response_minutes=d["first_response_minutes"],
                resolution_minutes=d["resolution_minutes"],
                is_active=True,
            )
            db.add(p)
            created.append(p)

        db.commit()
        return created

    @classmethod
    def evaluate_sla_deadlines(cls, db: Session, organization_id: str) -> Dict[str, Any]:
        """Idempotent evaluation of first response and resolution deadlines for active tickets."""
        now = datetime.now(timezone.utc)

        # Query all active non-closed tickets for this organization
        active_tickets = (
            db.query(Ticket)
            .filter(
                Ticket.organization_id == organization_id,
                Ticket.status.notin_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
            .all()
        )

        # Find manager to receive escalations if needed
        manager = (
            db.query(User)
            .filter(User.organization_id == organization_id, User.role == UserRole.SUPPORT_MANAGER)
            .first()
        )

        warnings_triggered = 0
        breaches_triggered = 0
        escalations_triggered = 0

        for t in active_tickets:
            # 1. First-Response Deadline Evaluation
            if not t.first_responded_at and t.first_response_deadline:
                # Handle SQLite naive datetimes by ensuring comparison is timezone aware
                deadline = t.first_response_deadline
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)

                remaining_minutes = (deadline - now).total_seconds() / 60.0

                if remaining_minutes <= 0:
                    # Breached
                    event_type = "first_response_breached"
                    if not cls._event_exists(db, t.id, event_type):
                        cls._record_event_and_notify(
                            db=db,
                            ticket=t,
                            event_type=event_type,
                            deadline=deadline,
                            title=f"SLA Breached: {t.reference_number}",
                            message=f"Ticket '{t.subject}' missed the first response deadline.",
                            notif_type="sla_breach",
                        )
                        breaches_triggered += 1

                        # Auto-escalate to manager if unassigned
                        if not t.assigned_agent_id and manager:
                            t.assigned_agent_id = manager.id
                            escalations_triggered += 1
                            AuditService.log_event(
                                db=db,
                                organization_id=organization_id,
                                action="ticket.escalated_to_manager",
                                entity_type="ticket",
                                entity_id=t.id,
                                details={"reason": "SLA first response breached while unassigned"},
                            )

                elif remaining_minutes <= 30:
                    # Approaching Warning
                    event_type = "first_response_warning"
                    if not cls._event_exists(db, t.id, event_type):
                        cls._record_event_and_notify(
                            db=db,
                            ticket=t,
                            event_type=event_type,
                            deadline=deadline,
                            title=f"SLA Warning: {t.reference_number}",
                            message=f"Ticket '{t.subject}' has {int(remaining_minutes)} mins remaining for first response.",
                            notif_type="sla_warning",
                        )
                        warnings_triggered += 1

            # 2. Resolution Deadline Evaluation
            if t.resolution_deadline:
                deadline = t.resolution_deadline
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)

                remaining_minutes = (deadline - now).total_seconds() / 60.0

                if remaining_minutes <= 0:
                    event_type = "resolution_breached"
                    if not cls._event_exists(db, t.id, event_type):
                        cls._record_event_and_notify(
                            db=db,
                            ticket=t,
                            event_type=event_type,
                            deadline=deadline,
                            title=f"Resolution SLA Breached: {t.reference_number}",
                            message=f"Ticket '{t.subject}' exceeded resolution deadline.",
                            notif_type="sla_breach",
                        )
                        breaches_triggered += 1
                elif remaining_minutes <= 60:
                    event_type = "resolution_warning"
                    if not cls._event_exists(db, t.id, event_type):
                        cls._record_event_and_notify(
                            db=db,
                            ticket=t,
                            event_type=event_type,
                            deadline=deadline,
                            title=f"Resolution SLA Warning: {t.reference_number}",
                            message=f"Ticket '{t.subject}' has {int(remaining_minutes)} mins remaining for resolution.",
                            notif_type="sla_warning",
                        )
                        warnings_triggered += 1

        db.commit()

        return {
            "active_tickets_evaluated": len(active_tickets),
            "warnings_triggered": warnings_triggered,
            "breaches_triggered": breaches_triggered,
            "escalations_triggered": escalations_triggered,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _event_exists(db: Session, ticket_id: str, event_type: str) -> bool:
        """Check if an SLA event has already occurred for this ticket (idempotency guard)."""
        return (
            db.query(SLAEvent)
            .filter(SLAEvent.ticket_id == ticket_id, SLAEvent.event_type == event_type)
            .first()
            is not None
        )

    @staticmethod
    def _record_event_and_notify(
        db: Session,
        ticket: Ticket,
        event_type: str,
        deadline: datetime,
        title: str,
        message: str,
        notif_type: str,
    ) -> None:
        """Create SLA event record and deliver in-app notification without duplicates."""
        event = SLAEvent(
            ticket_id=ticket.id,
            event_type=event_type,
            target_deadline=deadline,
            occurred_at=datetime.now(timezone.utc),
            notification_sent=True,
        )
        db.add(event)

        # In-app notification for assigned agent (or all org members if unassigned)
        notif = Notification(
            organization_id=ticket.organization_id,
            user_id=ticket.assigned_agent_id,
            title=title,
            message=message,
            notification_type=notif_type,
            reference_url=f"/tickets/{ticket.id}",
            is_read=False,
        )
        db.add(notif)
