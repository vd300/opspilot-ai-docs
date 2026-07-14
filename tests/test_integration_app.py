import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_route_uses_global_exception_shape() -> None:
    client = TestClient(create_app())

    response = client.get("/missing", headers={"X-Request-ID": "missing-route"})

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Not Found",
            "request_id": "missing-route",
        }
    }


def test_request_id_appears_in_request_logs(caplog) -> None:
    client = TestClient(create_app())

    with caplog.at_level(logging.INFO, logger="opspilot.requests"):
        response = client.get("/health", headers={"X-Request-ID": "log-request-123"})

    assert response.status_code == 200
    assert any(
        record.message == "request_completed"
        and getattr(record, "request_id", None) == "log-request-123"
        for record in caplog.records
    )

