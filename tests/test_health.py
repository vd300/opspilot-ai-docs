from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "OpsPilot AI"
    assert "x-request-id" in response.headers


def test_ready_returns_structured_checks() -> None:
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert isinstance(body["checks"], list)
    assert {check["name"] for check in body["checks"]} == {
        "application",
        "configuration",
    }


def test_request_id_header_is_preserved() -> None:
    client = TestClient(create_app())

    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-123"

