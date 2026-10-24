"""Unit and integration tests for background Celery worker tasks."""

from app.workers.tasks import async_classify_ticket, check_all_sla_breaches, async_generate_copilot_draft
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.organization import Organization
from app.models.sla import SLAPolicy


def test_celery_worker_tasks_direct_invocation(db_session):
    # 1. Setup organization and ticket
    org = Organization(name="Celery Worker Org", slug="celery-org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    ticket = Ticket(
        organization_id=org.id,
        reference_number="RES-CELERY-001",
        customer_name="Andy Bernard",
        customer_email="andy@cornell.edu",
        subject="Trouble logging in with single sign on",
        description="I am getting an invalid SAML assertion error code 403 on the login portal.",
        category=TicketCategory.GENERAL,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)

    # 2. Invoke async classification task synchronously
    result = async_classify_ticket(ticket.id)
    assert result is not None
    assert result["status"] == "success"
    assert result["category"] == "account"

    # Refresh ticket and verify classification updated
    db_session.refresh(ticket)
    assert ticket.category == TicketCategory.ACCOUNT

    # 3. Invoke async draft generation task
    draft_res = async_generate_copilot_draft(ticket.id)
    assert draft_res is not None
    assert draft_res["status"] == "success"

    # 4. Invoke periodic SLA breach check
    sla_res = check_all_sla_breaches()
    assert sla_res is not None
    assert sla_res["status"] == "success"
    assert "evaluated_tickets" in sla_res
