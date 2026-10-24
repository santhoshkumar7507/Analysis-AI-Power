"""Automated tests for Knowledge Base upload, text chunking, and tenant-isolated vector retrieval."""

import io
import pytest


def test_knowledge_document_upload_chunking_and_retrieval(client):
    # 1. Register organization and obtain admin token
    res = client.post("/api/v1/auth/register", json={
        "organization_name": "CloudDocs Enterprise",
        "email": "docs.admin@clouddocs.com",
        "password": "Password123!",
        "full_name": "Docs Admin",
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload sample company policy document
    policy_content = (
        "# Enterprise Refund and Billing Policy\n\n"
        "Customers requesting a refund within 30 days of initial subscription are entitled to a full 100% refund.\n"
        "Duplicate charges will be processed immediately upon verification with invoice receipts.\n\n"
        "# Service Level Agreements\n\n"
        "Critical priority incidents require an initial response within 1 hour and full resolution within 4 hours.\n"
        "High priority incidents must be resolved within 8 business hours."
    )

    file_obj = io.BytesIO(policy_content.encode("utf-8"))
    upload_res = client.post(
        "/api/v1/knowledge/documents",
        data={"title": "Official Billing & Refund Policy"},
        files={"file": ("billing_policy.md", file_obj, "text/markdown")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["chunk_count"] >= 2
    assert doc_data["status"] == "indexed"

    # 3. Test Semantic Retrieval for related refund inquiry
    search_res = client.post(
        "/api/v1/knowledge/search",
        json={"query": "How do I get a refund for duplicate charges?", "top_k": 3},
        headers=headers,
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_matches"] >= 1
    top_chunk = search_data["results"][0]
    assert "refund" in top_chunk["content"].lower()
    assert "Official Billing & Refund Policy" in top_chunk["citation"]
    assert top_chunk["similarity_score"] > 0.50

    # 4. Strict Tenant Isolation: Register a separate tenant and search with same query
    other_tenant_res = client.post("/api/v1/auth/register", json={
        "organization_name": "Rival Corp",
        "email": "rival@rival.com",
        "password": "Password123!",
        "full_name": "Rival Admin",
    })
    rival_headers = {"Authorization": f"Bearer {other_tenant_res.json()['access_token']}"}

    rival_search = client.post(
        "/api/v1/knowledge/search",
        json={"query": "How do I get a refund for duplicate charges?", "top_k": 3},
        headers=rival_headers,
    )
    assert rival_search.status_code == 200
    # Rival Corp has NO documents uploaded, so zero matches must be returned!
    assert rival_search.json()["total_matches"] == 0

    # 5. Delete document and verify chunks are purged
    del_res = client.delete(f"/api/v1/knowledge/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200

    # Search again after deletion -> 0 matches
    post_del_search = client.post(
        "/api/v1/knowledge/search",
        json={"query": "How do I get a refund for duplicate charges?", "top_k": 3},
        headers=headers,
    )
    assert post_del_search.json()["total_matches"] == 0
