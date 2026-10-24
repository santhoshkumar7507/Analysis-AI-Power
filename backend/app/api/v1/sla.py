"""SLA Policies and Monitoring API endpoints."""

from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.sla import SLAPolicy, SLAEvent
from app.services.sla_service import SLAService

router = APIRouter(prefix="/sla", tags=["SLA & Escalation Engine"])


class SLAPolicyUpdate(BaseModel):
    priority: str = Field(..., pattern="^(low|medium|high|critical)$")
    first_response_minutes: int = Field(..., ge=5, le=10080)
    resolution_minutes: int = Field(..., ge=15, le=43200)


@router.get("/policies")
def get_sla_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve organization SLA policies for all ticket priorities."""
    policies = SLAService.get_or_create_default_policies(db=db, organization_id=current_user.organization_id)
    return [
        {
            "id": p.id,
            "priority": p.priority,
            "first_response_minutes": p.first_response_minutes,
            "resolution_minutes": p.resolution_minutes,
            "is_active": p.is_active,
        }
        for p in policies
    ]


@router.put("/policies")
def update_sla_policy(
    req: SLAPolicyUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.SUPPORT_MANAGER])),
    db: Session = Depends(get_db),
):
    """Update SLA response or resolution deadline thresholds for a priority level."""
    policy = (
        db.query(SLAPolicy)
        .filter(SLAPolicy.organization_id == current_user.organization_id, SLAPolicy.priority == req.priority)
        .first()
    )
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")

    policy.first_response_minutes = req.first_response_minutes
    policy.resolution_minutes = req.resolution_minutes
    db.commit()
    db.refresh(policy)

    return {"message": f"SLA policy for {req.priority} updated successfully"}


@router.post("/evaluate")
def trigger_sla_evaluation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger an immediate SLA monitoring cycle to detect approaching warnings and breaches."""
    report = SLAService.evaluate_sla_deadlines(db=db, organization_id=current_user.organization_id)
    return report


@router.get("/events")
def list_sla_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recorded SLA warning, breach, and escalation audit events."""
    events = (
        db.query(SLAEvent)
        .order_by(SLAEvent.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": e.id,
            "ticket_id": e.ticket_id,
            "event_type": e.event_type,
            "target_deadline": e.target_deadline.isoformat(),
            "occurred_at": e.occurred_at.isoformat(),
        }
        for e in events
    ]
