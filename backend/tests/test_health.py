"""Tests for health and readiness probes."""


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "ResolveAI" in data["message"]
    assert "docs_url" in data


def test_liveness_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ResolveAI"
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_readiness_probe(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["database"] == "connected"
    assert "redis" in data["checks"]
