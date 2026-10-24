"""Automated tests proving strict multi-tenant boundary isolation."""


def test_strict_multi_tenant_isolation(client):
    # Register Tenant A
    res_a = client.post("/api/v1/auth/register", json={
        "organization_name": "Tenant Alpha",
        "email": "alpha.admin@alpha.com",
        "password": "Password123!",
        "full_name": "Alpha Admin",
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Tenant B
    res_b = client.post("/api/v1/auth/register", json={
        "organization_name": "Tenant Beta",
        "email": "beta.admin@beta.com",
        "password": "Password123!",
        "full_name": "Beta Admin",
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant Alpha creates a confidential ticket
    ticket_payload = {
        "customer_name": "Alpha Customer",
        "customer_email": "customer@alpha.com",
        "subject": "Alpha Confidential Billing Inquiry",
        "description": "Please review secret transaction #999.",
        "category": "billing",
        "priority": "high",
    }
    create_res = client.post("/api/v1/tickets", json=ticket_payload, headers=headers_a)
    assert create_res.status_code == 201
    ticket_a_id = create_res.json()["id"]

    # 1. Tenant Beta queries list of tickets -> MUST NOT contain Alpha's ticket
    list_b = client.get("/api/v1/tickets", headers=headers_b)
    assert list_b.status_code == 200
    beta_items = list_b.json()["items"]
    assert len(beta_items) == 0

    # 2. Tenant Beta attempts direct GET on Tenant Alpha's ticket -> MUST RETURN 404
    direct_get = client.get(f"/api/v1/tickets/{ticket_a_id}", headers=headers_b)
    assert direct_get.status_code == 404

    # 3. Tenant Beta attempts to update Tenant Alpha's ticket -> MUST RETURN 404
    patch_res = client.patch(
        f"/api/v1/tickets/{ticket_a_id}",
        json={"status": "resolved"},
        headers=headers_b,
    )
    assert patch_res.status_code == 404

    # 4. Tenant Beta attempts to post a message to Tenant Alpha's ticket -> MUST RETURN 404
    msg_res = client.post(
        f"/api/v1/tickets/{ticket_a_id}/messages",
        json={"body": "Hacker note", "is_internal_note": True},
        headers=headers_b,
    )
    assert msg_res.status_code == 404
