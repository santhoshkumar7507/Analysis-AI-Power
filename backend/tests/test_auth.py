"""Automated tests for authentication, user registration, JWT issuance, and RBAC."""

import pytest


def test_register_organization_and_admin(client):
    payload = {
        "organization_name": "Apex Enterprise",
        "email": "admin@apex.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Apex Administrator",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "admin@apex.com"
    assert data["user"]["role"] == "admin"
    assert data["organization"]["name"] == "Apex Enterprise"


def test_register_duplicate_email_fails(client):
    payload = {
        "organization_name": "Apex Duplicate",
        "email": "admin@apex.com",  # already registered in previous test
        "password": "Password123!",
        "full_name": "Another Admin",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success_and_me_profile(client):
    login_payload = {
        "email": "admin@apex.com",
        "password": "SuperSecretPassword123!",
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Verify /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "admin@apex.com"
    assert me_data["role"] == "admin"


def test_login_invalid_credentials_fails(client):
    login_payload = {
        "email": "admin@apex.com",
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


def test_invite_member_and_role_enforcement(client):
    # Login as admin
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@apex.com", "password": "SuperSecretPassword123!"})
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Invite an agent
    agent_payload = {
        "email": "agent.smith@apex.com",
        "full_name": "Agent Smith",
        "password": "AgentPassword123!",
        "role": "support_agent",
    }
    invite_res = client.post("/api/v1/auth/members", json=agent_payload, headers=admin_headers)
    assert invite_res.status_code == 201
    assert invite_res.json()["role"] == "support_agent"

    # Login as agent
    agent_login = client.post("/api/v1/auth/login", json={"email": "agent.smith@apex.com", "password": "AgentPassword123!"})
    assert agent_login.status_code == 200
    agent_token = agent_login.json()["access_token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    # Verify agent cannot invite members (requires admin or manager)
    sub_invite = client.post("/api/v1/auth/members", json={
        "email": "rogue@apex.com",
        "full_name": "Rogue Agent",
        "password": "Password123!",
        "role": "support_agent",
    }, headers=agent_headers)
    assert sub_invite.status_code == 403
