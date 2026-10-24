"""Automated tests for Analytics metrics calculation, AI benchmark endpoint, and CSV formula sanitization."""

import pytest


def test_analytics_overview_and_csv_export(client):
    # 1. Register organization and obtain token
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "Metrics Global",
        "email": "metrics.admin@global.com",
        "password": "Password123!",
        "full_name": "Metrics Admin",
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create sample tickets including one with a potentially malicious formula in the subject
    client.post("/api/v1/tickets", json={
        "customer_name": "Attacker Test",
        "customer_email": "attacker@test.com",
        "subject": "=cmd|' /C calc'!A0",  # CSV Injection payload
        "description": "Testing Excel formula injection defense.",
        "category": "technical",
        "priority": "critical",
    }, headers=headers)

    client.post("/api/v1/tickets", json={
        "customer_name": "Normal Customer",
        "customer_email": "normal@test.com",
        "subject": "Inquiry regarding billing invoice",
        "description": "Please check our standard invoice.",
        "category": "billing",
        "priority": "medium",
    }, headers=headers)

    # 3. Test Analytics Overview
    overview_res = client.get("/api/v1/analytics/overview", headers=headers)
    assert overview_res.status_code == 200
    data = overview_res.json()
    assert data["total_tickets"] >= 2
    assert "category_distribution" in data
    assert "priority_distribution" in data
    assert "sla_compliance_rate" in data

    # 4. Test AI Benchmark Performance Endpoint
    ai_perf_res = client.get("/api/v1/analytics/ai-performance")
    assert ai_perf_res.status_code == 200
    ai_data = ai_perf_res.json()
    assert ai_data["total_samples"] == 10
    assert ai_data["f1_score"] >= 0.80

    # 5. Test CSV Export & Formula Injection Sanitization
    export_res = client.get("/api/v1/analytics/export", headers=headers)
    assert export_res.status_code == 200
    assert export_res.headers["content-type"].startswith("text/csv")
    csv_text = export_res.text

    # The formula payload must be prepended with a single quote to neutralize execution in Excel!
    assert "'=cmd|' /C calc'!A0" in csv_text
    assert "Reference Number,Customer Name" in csv_text
