"""Automated tests for ticket lifecycle, conversation history, and status transitions."""


def test_ticket_lifecycle_and_conversations(client):
    # Register & Login
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "Helios Cloud",
        "email": "lead@helios.com",
        "password": "Password123!",
        "full_name": "Helios Lead",
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Ticket
    create_res = client.post("/api/v1/tickets", json={
        "customer_name": "Jane Doe",
        "customer_email": "jane@example.com",
        "subject": "Cannot reset enterprise SSO password",
        "description": "I receive a 403 error when attempting SAML redirect.",
        "category": "technical",
        "priority": "critical",
    }, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    ticket_id = data["id"]
    ref_num = data["reference_number"]
    assert "RES-" in ref_num

    # 2. Get Ticket Detail
    detail_res = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
    assert detail_res.status_code == 200
    ticket = detail_res.json()
    assert ticket["reference_number"] == ref_num
    assert ticket["status"] == "open"
    assert len(ticket["messages"]) == 1  # initial customer description
    assert ticket["messages"][0]["sender_type"] == "customer"
    assert ticket["first_response_deadline"] is not None

    # 3. Add an Internal Team Note
    note_res = client.post(f"/api/v1/tickets/{ticket_id}/messages", json={
        "body": "Checking SAML cert expiration in Auth0 logs.",
        "is_internal_note": True,
    }, headers=headers)
    assert note_res.status_code == 201
    assert note_res.json()["is_internal_note"] is True

    # 4. Agent posts customer-facing reply
    reply_res = client.post(f"/api/v1/tickets/{ticket_id}/messages", json={
        "body": "Hello Jane, we have identified a cert rollover issue and regenerated your SAML metadata.",
        "is_internal_note": False,
    }, headers=headers)
    assert reply_res.status_code == 201

    # Check that ticket automatically transitioned from open to in_progress and recorded first_responded_at
    refreshed_ticket = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).json()
    assert refreshed_ticket["status"] == "in_progress"
    assert refreshed_ticket["first_responded_at"] is not None
    assert len(refreshed_ticket["messages"]) == 3

    # 5. Resolve Ticket
    patch_res = client.patch(f"/api/v1/tickets/{ticket_id}", json={
        "status": "resolved",
    }, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "resolved"

    resolved_ticket = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).json()
    assert resolved_ticket["resolved_at"] is not None


def test_ticket_filtering_and_search(client):
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "Filter Org",
        "email": "filter@org.com",
        "password": "Password123!",
        "full_name": "Filter Admin",
    })
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    # Create multiple tickets with different categories
    client.post("/api/v1/tickets", json={
        "customer_name": "Alice Billing",
        "customer_email": "alice@bill.com",
        "subject": "Refund requested for invoice #102",
        "description": "Double charged on annual plan.",
        "category": "refunds",
        "priority": "high",
    }, headers=headers)

    client.post("/api/v1/tickets", json={
        "customer_name": "Bob Tech",
        "customer_email": "bob@code.com",
        "subject": "API webhook 500 error",
        "description": "Endpoints returning internal error.",
        "category": "technical",
        "priority": "low",
    }, headers=headers)

    # Filter by category
    filter_res = client.get("/api/v1/tickets?category=refunds", headers=headers)
    assert filter_res.status_code == 200
    items = filter_res.json()["items"]
    assert len(items) == 1
    assert items[0]["customer_name"] == "Alice Billing"

    # Search keyword
    search_res = client.get("/api/v1/tickets?search=webhook", headers=headers)
    assert search_res.status_code == 200
    search_items = search_res.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["customer_name"] == "Bob Tech"
