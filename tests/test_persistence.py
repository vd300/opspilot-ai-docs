from pathlib import Path

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.dependencies import GraphDependencies
from app.graph.workflow import run_investigation_workflow
from app.main import create_app
from app.persistence import InvestigationNotFoundError, SQLiteInvestigationRepository
from app.router import OpsRoute, RouteDecision, RouterInput
from app.schemas.investigations import InvestigationRequest


class FakeRouter:
    def __init__(self, route: OpsRoute = OpsRoute.INCIDENT_INVESTIGATION) -> None:
        self.selected_route = route
        self.calls: list[RouterInput] = []

    def route(self, router_input: RouterInput, *, request_id: str | None = None):
        self.calls.append(router_input)
        return RouteDecision(
            route=self.selected_route,
            service_name=router_input.service_name or "checkout-service",
            incident_id=router_input.incident_id,
            confidence=0.95,
            reason="Test router selected a deterministic route.",
            fallback_used=True,
        )


def dependencies(database_path: Path) -> GraphDependencies:
    return GraphDependencies(
        router=FakeRouter(),  # type: ignore[arg-type]
        investigation_repository=SQLiteInvestigationRepository(database_path),
        checkpointer=InMemorySaver(),
    )


def investigation_request() -> InvestigationRequest:
    return InvestigationRequest(
        question="Why is checkout-service returning HTTP 500 after the latest deployment?",
        service_name="checkout-service",
        incident_id="INC-001",
        environment="production",
    )


def test_investigation_is_persisted_with_internal_state(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")

    response = run_investigation_workflow(
        investigation_request(),
        request_id="req-persist",
        dependencies=deps,
    )

    record = deps.investigation_repository.get_investigation(response.investigation_id)
    assert record.request_id == "req-persist"
    assert record.response["investigation_id"] == response.investigation_id
    assert record.state["final_response"]["investigation_id"] == response.investigation_id
    assert record.checkpoint_thread_id == response.investigation_id


def test_missing_investigation_raises_not_found(tmp_path: Path) -> None:
    repository = SQLiteInvestigationRepository(tmp_path / "opspilot.sqlite3")

    try:
        repository.get_response("missing-investigation")
    except InvestigationNotFoundError as exc:
        assert exc.args == ("missing-investigation",)
    else:
        raise AssertionError("Missing investigation did not raise.")


def test_workflow_creates_langgraph_checkpoint(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")

    response = run_investigation_workflow(
        investigation_request(),
        request_id="req-checkpoint",
        dependencies=deps,
    )

    checkpoint = deps.checkpointer.get_tuple(
        {"configurable": {"thread_id": response.investigation_id}}
    )
    assert checkpoint is not None


def test_tool_calls_and_subagent_results_are_persisted(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")

    response = run_investigation_workflow(
        investigation_request(),
        request_id="req-tool-calls",
        dependencies=deps,
    )

    repository = deps.investigation_repository
    tool_calls = repository.list_tool_calls(response.investigation_id)
    subagent_results = repository.list_subagent_results(response.investigation_id)
    assert {row["agent"] for row in subagent_results} == {
        "deployment_analysis",
        "log_analysis",
        "metrics_analysis",
        "runbook_analysis",
    }
    assert any(row["tool_name"] == "log_investigation" for row in tool_calls)
    assert any(row["tool_name"] == "get_metrics" for row in tool_calls)
    assert any(row["source_id"] == "log-inc001-140301" for row in tool_calls)


def test_handoff_event_is_persisted(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")

    response = run_investigation_workflow(
        investigation_request(),
        request_id="req-handoff",
        dependencies=deps,
    )

    events = deps.investigation_repository.list_handoff_events(response.investigation_id)
    assert len(events) == 1
    assert events[0]["target_agent"] == "database_specialist"
    assert events[0]["reason"] == response.handoff_reason
    assert events[0]["decision_json"]["should_handoff"] is True
    assert events[0]["result_json"]["agent"] == "database_specialist"


def test_get_investigation_loads_persisted_response(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))

    created = client.post(
        "/api/v1/investigations",
        json=investigation_request().model_dump(mode="json"),
        headers={"X-Request-ID": "req-api-persist"},
    )
    investigation_id = created.json()["investigation_id"]

    loaded = client.get(f"/api/v1/investigations/{investigation_id}")

    assert loaded.status_code == 200
    assert loaded.json() == created.json()


def test_get_investigation_returns_404_for_missing_id(tmp_path: Path) -> None:
    deps = dependencies(tmp_path / "opspilot.sqlite3")
    client = TestClient(create_app(graph_dependencies=deps))

    response = client.get("/api/v1/investigations/missing-id")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Investigation not found."


def test_restart_recovery_uses_durable_repository(tmp_path: Path) -> None:
    database_path = tmp_path / "opspilot.sqlite3"
    first_client = TestClient(create_app(graph_dependencies=dependencies(database_path)))
    created = first_client.post(
        "/api/v1/investigations",
        json=investigation_request().model_dump(mode="json"),
        headers={"X-Request-ID": "req-restart"},
    )
    investigation_id = created.json()["investigation_id"]

    restarted_deps = dependencies(database_path)
    restarted_client = TestClient(create_app(graph_dependencies=restarted_deps))
    recovered = restarted_client.get(f"/api/v1/investigations/{investigation_id}")

    assert recovered.status_code == 200
    assert recovered.json()["investigation_id"] == investigation_id
    assert recovered.json()["request_id"] == "req-restart"
