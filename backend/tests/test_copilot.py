"""Automated tests for AI Copilot classification, grounded RAG draft generation, approval, and evaluation."""

import io
import pytest
from app.ai.evaluation import AIEvaluationBenchmark


def test_ai_copilot_classification_and_draft_approval(client):
    # 1. Register organization and obtain token
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "Copilot Test Org",
        "email": "copilot.admin@test.com",
        "password": "Password123!",
        "full_name": "Copilot Admin",
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload policy document for grounding
    policy_doc = (
        "# Refund Policies\n\n"
        "Customers requesting a refund within 30 days are entitled to a 100% full refund on their subscription.\n"
        "All refund requests must be verified by billing agents."
    )
    client.post(
        "/api/v1/knowledge/documents",
        data={"title": "Official Refund Policy"},
        files={"file": ("refund_policy.md", io.BytesIO(policy_doc.encode("utf-8")), "text/markdown")},
        headers=headers,
    )

    # 3. Create ticket
    ticket_res = client.post("/api/v1/tickets", json={
        "customer_name": "David Wallace",
        "customer_email": "d.wallace@dunder.com",
        "subject": "Need a refund for annual subscription cancellation",
        "description": "We canceled our subscription 5 days after sign up. Please issue a refund.",
        "category": "refunds",
        "priority": "high",
    }, headers=headers)
    assert ticket_res.status_code == 201
    ticket_id = ticket_res.json()["id"]

    # 4. Trigger / Fetch AI Analysis
    analysis_res = client.get(f"/api/v1/tickets/{ticket_id}/ai-analysis", headers=headers)
    assert analysis_res.status_code == 200
    analysis = analysis_res.json()
    assert analysis["category"] == "refunds"
    assert analysis["priority"] in ["high", "critical", "medium"]
    assert "refund" in analysis["issue_summary"].lower()
    assert analysis["confidence_score"] > 0.70

    # 5. Generate Grounded AI Reply Draft
    gen_res = client.post(f"/api/v1/tickets/{ticket_id}/copilot/generate", headers=headers)
    assert gen_res.status_code == 200
    draft = gen_res.json()
    assert draft["is_grounded"] is True
    assert len(draft["citations"]) >= 1
    assert "Official Refund Policy" in draft["citations"][0]["citation"]
    assert "100%" in draft["suggested_reply"] or "refund" in draft["suggested_reply"].lower()

    # 6. Approve Draft with manual edit
    edited_text = draft["suggested_reply"] + "\n\nPS: Your account manager will follow up."
    approve_res = client.post(
        f"/api/v1/tickets/{ticket_id}/copilot/approve",
        json={"edited_reply": edited_text, "review_comment": "Verified and edited with custom PS."},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "edited_and_approved"

    # Verify message now exists in ticket conversation thread
    ticket_detail = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers).json()
    messages = ticket_detail["messages"]
    assert any(edited_text in m["body"] for m in messages)


def test_ai_copilot_draft_rejection(client):
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "Reject Test Org",
        "email": "reject.admin@test.com",
        "password": "Password123!",
        "full_name": "Reject Admin",
    })
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    ticket_res = client.post("/api/v1/tickets", json={
        "customer_name": "Toby Flenderson",
        "customer_email": "toby@dunder.com",
        "subject": "HR policy question",
        "description": "Where can I find the employee handbook?",
    }, headers=headers)
    ticket_id = ticket_res.json()["id"]

    # Generate Draft
    client.post(f"/api/v1/tickets/{ticket_id}/copilot/generate", headers=headers)

    # Reject Draft
    reject_res = client.post(
        f"/api/v1/tickets/{ticket_id}/copilot/reject",
        json={"rejection_reason": "Tone is too informal for an HR ticket."},
        headers=headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"


def test_ai_evaluation_benchmark_metrics():
    """Verify that the AI evaluation benchmark executes and computes verifiable Precision, Recall, and F1."""
    report = AIEvaluationBenchmark.run_benchmark()
    assert report["total_samples"] == 10
    assert report["accuracy_score"] >= 0.80
    assert report["precision_score"] >= 0.80
    assert report["recall_score"] >= 0.80
    assert report["f1_score"] >= 0.80
    assert report["avg_latency_ms"] < 100.0  # Fast local performance
