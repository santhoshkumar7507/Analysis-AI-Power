"""Automated tests for SLA policies, deadline calculations, and idempotent escalation."""

from datetime import datetime, timedelta, timezone
import pytest
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.core.database import SessionLocal


def test_sla_policies_and_idempotent_evaluation(client):
    # 1. Register organization and obtain token
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "SLA Enterprise",
        "email": "sla.admin@enterprise.com",
        "password": "Password123!",
        "full_name": "SLA Admin",
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Default Policies
    policies_res = client.get("/api/v1/sla/policies", headers=headers)
    assert policies_res.status_code == 200
    policies = policies_res.json()
    assert len(policies) == 4
    critical_policy = next(p for p in policies if p["priority"] == "critical")
    assert critical_policy["first_response_minutes"] == 60

    # 3. Update Policy
    update_res = client.put(
        "/api/v1/sla/policies",
        json={"priority": "critical", "first_response_minutes": 45, "resolution_minutes": 180},
        headers=headers,
    )
    assert update_res.status_code == 200

    # 4. Create an Overdue Ticket directly in DB (simulating an expired deadline)
    db = SessionLocal()
    org_id = res.json()["organization"]["id"]
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)

    overdue_ticket = Ticket(
        organization_id=org_id,
        reference_number="RES-SLA-TEST-01",
        customer_name="Urgent Customer",
        customer_email="urgent@test.com",
        subject="Critical Outage Exceeding SLA",
        description="Systems unreachable for 2 hours.",
        category="technical",
        priority="critical",
        status=TicketStatus.OPEN,
        first_response_deadline=past_time,
        resolution_deadline=past_time + timedelta(hours=1),
        created_at=past_time - timedelta(hours=1),
    )
    db.add(overdue_ticket)
    db.commit()
    ticket_id = overdue_ticket.id
    db.close()

    # 5. Run SLA Evaluation Cycle 1
    eval_res1 = client.post("/api/v1/sla/evaluate", headers=headers)
    assert eval_res1.status_code == 200
    report1 = eval_res1.json()
    assert report1["breaches_triggered"] >= 1

    # 6. Strict Idempotency Check: Run SLA Evaluation 4 more times
    # Repeated cycles MUST NOT trigger duplicate breach events or notifications!
    for _ in range(4):
        repeat_res = client.post("/api/v1/sla/evaluate", headers=headers)
        assert repeat_res.status_code == 200
        repeat_report = repeat_res.json()
        assert repeat_report["breaches_triggered"] == 0
        assert repeat_report["warnings_triggered"] == 0

    # 7. Check In-App Notifications
    notif_res = client.get("/api/v1/notifications", headers=headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    assert len(notifs) >= 1
    sla_notif = notifs[0]
    assert "SLA Breached" in sla_notif["title"]
    assert sla_notif["is_read"] is False

    # Mark as read
    read_res = client.patch(f"/api/v1/notifications/{sla_notif['id']}/read", headers=headers)
    assert read_res.status_code == 200
