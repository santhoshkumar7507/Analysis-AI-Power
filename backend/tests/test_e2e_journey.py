"""End-to-End Integration Journey Test for ResolveAI Platform."""

import io
import pytest


def test_complete_enterprise_support_journey(client):
    # STEP 1: Organization Onboarding & Administrator Auth
    reg_res = client.post("/api/v1/auth/register", json={
        "organization_name": "Titan Aerospace Logistics",
        "email": "sarah.lead@titan.com",
        "password": "SecurePassword123!",
        "full_name": "Sarah Lead",
    })
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # STEP 2: Administrator Indexes Company Policy in Knowledge Base
    company_policy = (
        "# Titan Aerospace Refund and Defect Warranty Policy\n\n"
        "Customers experiencing hardware component delivery delays exceeding 48 hours are eligible for an immediate expedited replacement.\n"
        "All refund requests processed within the warranty period of 30 days are entitled to a full 100% refund upon receipt of serial number validation.\n\n"
        "# Technical Escalation Procedures\n\n"
        "API errors on the logistics tracking portal must be escalated to the Tier 2 avionics team."
    )
    upload_res = client.post(
        "/api/v1/knowledge/documents",
        data={"title": "Titan Warranty and Refund Policy"},
        files={"file": ("warranty_policy.md", io.BytesIO(company_policy.encode("utf-8")), "text/markdown")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["chunk_count"] >= 2

    # STEP 3: Customer Submits a Support Ticket
    ticket_payload = {
        "customer_name": "Commander Mark Watney",
        "customer_email": "m.watney@ares3.org",
        "subject": "Hardware component delivery delayed beyond 48 hours, requesting replacement and refund details",
        "description": "Our telemetry rover antenna has not arrived and tracking is stagnant. According to policy we need an expedited replacement or full refund.",
        "category": "refunds",
        "priority": "high",
        "channel": "web",
    }
    create_ticket_res = client.post("/api/v1/tickets", json=ticket_payload, headers=headers)
    assert create_ticket_res.status_code == 201
    ticket_id = create_ticket_res.json()["id"]
    ref_number = create_ticket_res.json()["reference_number"]
    assert "RES-" in ref_number

    # STEP 4: AI Ticket Intelligence Classification
    ai_analysis_res = client.get(f"/api/v1/tickets/{ticket_id}/ai-analysis", headers=headers)
    assert ai_analysis_res.status_code == 200
    analysis = ai_analysis_res.json()
    assert analysis["category"] in ["refunds", "orders", "general"]
    assert analysis["confidence_score"] > 0.70

    # STEP 5: AI Copilot RAG Grounded Reply Synthesis
    copilot_gen_res = client.post(f"/api/v1/tickets/{ticket_id}/copilot/generate", headers=headers)
    assert copilot_gen_res.status_code == 200
    draft_data = copilot_gen_res.json()
    assert draft_data["is_grounded"] is True
    assert len(draft_data["citations"]) >= 1
    assert "Titan Warranty and Refund Policy" in draft_data["citations"][0]["citation"]

    # STEP 6: Support Agent Edits & Approves Draft (Human-in-the-Loop)
    agent_edited_reply = (
        draft_data["suggested_reply"] + "\n\nWe have dispatched priority courier tracking code #ARES-8891."
    )
    approve_res = client.post(
        f"/api/v1/tickets/{ticket_id}/copilot/approve",
        json={"edited_reply": agent_edited_reply, "review_comment": "Verified courier dispatch with logistics lead."},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "edited_and_approved"

    # STEP 7: Verify Conversation History Updated & First Response Recorded
    ticket_after_reply = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).json()
    assert ticket_after_reply["status"] == "in_progress"
    assert ticket_after_reply["first_responded_at"] is not None
    assert len(ticket_after_reply["messages"]) == 2  # 1 customer + 1 approved agent reply

    # STEP 8: Agent Resolves the Ticket
    resolve_res = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"

    resolved_ticket = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).json()
    assert resolved_ticket["resolved_at"] is not None

    # STEP 9: Verify Analytics Updated
    metrics_res = client.get("/api/v1/analytics/overview", headers=headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert metrics["total_tickets"] >= 1
    assert metrics["resolved_tickets"] >= 1
    assert metrics["average_first_response_minutes"] >= 0.0
