from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.dependencies import GraphDependencies
from app.main import create_app
from app.persistence import SQLiteInvestigationRepository
from app.router import OpsRoute, RouteDecision, RouterInput
from app.schemas.investigations import InvestigationResponse


class FakeRouter:
    def route(self, router_input: RouterInput, *, request_id: str | None = None):
        return RouteDecision(
            route=OpsRoute.INCIDENT_INVESTIGATION,
            service_name=router_input.service_name or "checkout-service",
            incident_id=router_input.incident_id,
            confidence=0.95,
            reason="Test router selected incident investigation.",
            fallback_used=True,
        )


def dependencies(database_path: Path) -> GraphDependencies:
    return GraphDependencies(
        router=FakeRouter(),  # type: ignore[arg-type]
        investigation_repository=SQLiteInvestigationRepository(database_path),
        checkpointer=InMemorySaver(),
    )


def create_pending(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/investigations",
        json={
            "question": "Why is checkout-service returning HTTP 500 after the latest deployment?",
            "service_name": "checkout-service",
            "incident_id": "INC-001",
            "environment": "production",
        },
        headers={"X-Request-ID": "req-create-approval"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approval_required"
    assert body["approval_status"] == "pending"
    return body


def test_approval_endpoint_approves_and_simulates_rollback(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))
    pending = create_pending(client)

    response = client.post(
        f"/api/v1/investigations/{pending['investigation_id']}/approval",
        json={"decision": "approve", "decided_by": "incident-commander"},
        headers={"X-Request-ID": "req-approve"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rollback_simulated"
    assert body["requires_approval"] is False
    assert body["approval_status"] == "approved"
    assert body["approval_result"]["executed"] is True
    assert body["approval_result"]["mode"] == "simulated"
    audit = deps.investigation_repository.list_approval_audit(pending["investigation_id"])
    assert len(audit) == 1
    assert audit[0]["decision"] == "approve"
    assert audit[0]["outcome"] == "approved"


def test_approval_endpoint_rejects_without_rollback(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))
    pending = create_pending(client)

    response = client.post(
        f"/api/v1/investigations/{pending['investigation_id']}/approval",
        json={
            "decision": "reject",
            "decided_by": "incident-commander",
            "comment": "Wait for database owner review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approval_rejected"
    assert body["approval_status"] == "rejected"
    assert body["approval_result"]["executed"] is False
    assert "database owner" in body["approval_result"]["reason"]


def test_duplicate_approval_decision_is_rejected(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))
    pending = create_pending(client)
    path = f"/api/v1/investigations/{pending['investigation_id']}/approval"
    payload = {"decision": "approve", "decided_by": "incident-commander"}

    assert client.post(path, json=payload).status_code == 200
    duplicate = client.post(path, json=payload)

    assert duplicate.status_code == 409
    assert "already been decided" in duplicate.json()["error"]["message"]


def test_invalid_approval_decision_uses_request_validation(tmp_path: Path) -> None:
    client = TestClient(create_app(graph_dependencies=dependencies(tmp_path / "opspilot.sqlite3")))
    pending = create_pending(client)

    response = client.post(
        f"/api/v1/investigations/{pending['investigation_id']}/approval",
        json={"decision": "maybe", "decided_by": "incident-commander"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_expired_approval_decision_is_not_executed(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))
    pending = create_pending(client)
    record = deps.investigation_repository.get_investigation(pending["investigation_id"])
    expired_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    state = {**record.state, "approval_expires_at": expired_at}
    response_data = {
        **record.response,
        "approval_expires_at": expired_at,
    }
    deps.investigation_repository.save_completed_investigation(
        state=state,
        response=InvestigationResponse.model_validate(response_data),
        checkpoint_thread_id=record.checkpoint_thread_id,
    )

    response = client.post(
        f"/api/v1/investigations/{pending['investigation_id']}/approval",
        json={"decision": "approve", "decided_by": "incident-commander"},
    )

    assert response.status_code == 409
    assert "expired" in response.json()["error"]["message"]
    updated = deps.investigation_repository.get_response(pending["investigation_id"])
    assert updated.status == "approval_expired"
    assert updated.approval_result is not None
    assert updated.approval_result["executed"] is False


def test_approval_resume_survives_application_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "opspilot.sqlite3"
    first_deps = dependencies(database_path)
    first_client = TestClient(create_app(graph_dependencies=first_deps))
    pending = create_pending(first_client)

    restarted_deps = dependencies(database_path)
    restarted_client = TestClient(create_app(graph_dependencies=restarted_deps))
    response = restarted_client.post(
        f"/api/v1/investigations/{pending['investigation_id']}/approval",
        json={"decision": "approve", "decided_by": "incident-commander"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rollback_simulated"
    assert response.json()["approval_result"]["executed"] is True
