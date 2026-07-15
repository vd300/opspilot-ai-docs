import pytest
from fastapi.testclient import TestClient

from app.graph.dependencies import GraphDependencies
from app.graph.nodes import (
    WorkflowExecutionError,
    WorkflowValidationError,
    create_investigation_plan,
    make_route_request_node,
    validate_request,
)
from app.graph.routing import ROUTE_TO_NODE, select_route_node
from app.graph.workflow import compile_investigation_graph, run_investigation_workflow
from app.main import create_app
from app.router import OpsRoute, RouteDecision, RouterInput
from app.schemas.investigations import InvestigationRequest


class FakeRouter:
    def __init__(self, decision: RouteDecision | BaseException) -> None:
        self.decision = decision
        self.calls: list[RouterInput] = []

    def route(self, router_input: RouterInput, *, request_id: str | None = None):
        self.calls.append(router_input)
        if isinstance(self.decision, BaseException):
            raise self.decision
        return self.decision


class InvalidRouteValue:
    value = "invalid_route"


class InvalidRouteDecision:
    route = InvalidRouteValue()
    service_name = "checkout-service"
    incident_id = None
    deployment_id = None
    confidence = 0.4
    reason = "Invalid route for fallback coverage."
    fallback_used = True


def decision(route: OpsRoute, *, service_name: str | None = "checkout-service") -> RouteDecision:
    return RouteDecision(
        route=route,
        service_name=service_name,
        confidence=0.91,
        reason=f"Selected {route.value}",
        fallback_used=True,
    )


def deps(route: OpsRoute) -> GraphDependencies:
    return GraphDependencies(router=FakeRouter(decision(route)))  # type: ignore[arg-type]


def request(question: str = "Why is checkout-service failing?") -> InvestigationRequest:
    return InvestigationRequest(
        question=question,
        service_name="checkout-service",
        environment="production",
    )


def test_validation_node_accepts_valid_request() -> None:
    result = validate_request(
        {
            "request_id": "req-1",
            "user_query": "  Why is CHECKOUT-SERVICE failing?  ",
            "service_name": "CHECKOUT-SERVICE",
            "incident_id": "inc-001",
            "environment": "Production",
            "errors": [],
        }
    )

    assert result["user_query"] == "Why is CHECKOUT-SERVICE failing?"
    assert result["service_name"] == "checkout-service"
    assert result["incident_id"] == "INC-001"
    assert result["environment"] == "production"
    assert result["investigation_id"]


def test_validation_node_rejects_empty_query() -> None:
    with pytest.raises(WorkflowValidationError):
        validate_request({"request_id": "req-1", "user_query": "   ", "errors": []})


def test_validation_node_preserves_existing_investigation_id() -> None:
    result = validate_request(
        {
            "request_id": "req-1",
            "investigation_id": "investigation-123",
            "user_query": "Who owns checkout-service?",
            "errors": [],
        }
    )

    assert result["investigation_id"] == "investigation-123"


def test_route_node_calls_router_and_stores_decision() -> None:
    fake_router = FakeRouter(decision(OpsRoute.SERVICE_LOOKUP, service_name="payment-service"))
    node = make_route_request_node(GraphDependencies(router=fake_router))  # type: ignore[arg-type]

    result = node(
        {
            "request_id": "req-1",
            "user_query": "Who owns payment-service?",
            "service_name": "payment-service",
            "incident_id": None,
            "investigation_id": "investigation-1",
        }
    )

    assert fake_router.calls[0].question == "Who owns payment-service?"
    assert result["route"] == "service_lookup"
    assert result["route_confidence"] == 0.91
    assert result["service_name"] == "payment-service"
    assert result["active_agent"] == "request_router"


def test_route_node_handles_router_failure() -> None:
    fake_router = FakeRouter(RuntimeError("router unavailable"))
    node = make_route_request_node(GraphDependencies(router=fake_router))  # type: ignore[arg-type]

    with pytest.raises(WorkflowExecutionError):
        node(
            {
                "request_id": "req-1",
                "user_query": "Who owns checkout-service?",
                "investigation_id": "investigation-1",
            }
        )


@pytest.mark.parametrize(
    ("route", "node"),
    [
        (OpsRoute.INCIDENT_INVESTIGATION, "create_investigation_plan"),
        (OpsRoute.SERVICE_LOOKUP, "service_lookup_response"),
        (OpsRoute.DEPLOYMENT_ANALYSIS, "deployment_analysis_response"),
        (OpsRoute.RUNBOOK_SEARCH, "runbook_search_response"),
        (OpsRoute.REPORT_GENERATION, "report_generation_response"),
        (OpsRoute.GENERAL_QUESTION, "general_question_response"),
    ],
)
def test_conditional_routing_covers_supported_routes(route: OpsRoute, node: str) -> None:
    assert ROUTE_TO_NODE[route.value] == node
    assert select_route_node({"route": route.value}) == node


def test_conditional_routing_sends_unknown_route_to_safe_fallback() -> None:
    assert select_route_node({"route": "invalid_route"}) == "unsupported_route_response"


def test_investigation_plan_is_created_only_by_plan_node() -> None:
    result = create_investigation_plan({"route": "incident_investigation"})

    assert "logs" in " ".join(result["investigation_plan"]).lower()
    assert "metrics" in " ".join(result["investigation_plan"]).lower()
    assert "deployments" in " ".join(result["investigation_plan"]).lower()
    assert "runbooks" in " ".join(result["investigation_plan"]).lower()
    assert "executed" not in " ".join(result["investigation_plan"]).lower()


def test_graph_compiles() -> None:
    assert compile_investigation_graph(deps(OpsRoute.GENERAL_QUESTION)) is not None


@pytest.mark.parametrize(
    ("route", "expected_status", "expected_plan"),
    [
        (OpsRoute.INCIDENT_INVESTIGATION, "preliminary_diagnosis", True),
        (OpsRoute.SERVICE_LOOKUP, "selected", False),
        (OpsRoute.DEPLOYMENT_ANALYSIS, "selected", False),
        (OpsRoute.RUNBOOK_SEARCH, "selected", False),
        (OpsRoute.REPORT_GENERATION, "selected", False),
        (OpsRoute.GENERAL_QUESTION, "selected", False),
    ],
)
def test_graph_reaches_end_for_every_supported_route(
    route: OpsRoute,
    expected_status: str,
    expected_plan: bool,
) -> None:
    response = run_investigation_workflow(
        request(),
        request_id="req-graph",
        dependencies=deps(route),
    )

    assert response.route == route
    assert response.status == expected_status
    assert bool(response.investigation_plan) is expected_plan
    assert response.request_id == "req-graph"


def test_graph_invalid_route_reaches_safe_failure_response() -> None:
    response = run_investigation_workflow(
        request(),
        request_id="req-invalid-route",
        dependencies=GraphDependencies(router=FakeRouter(InvalidRouteDecision())),  # type: ignore[arg-type]
    )

    assert response.route == "invalid_route"
    assert response.status == "unsupported_route"
    assert response.investigation_plan == []


def test_investigation_endpoint_accepts_valid_request() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/investigations",
        json={
            "question": "Why is checkout-service failing after the latest deployment?",
            "service_name": "checkout-service",
            "environment": "production",
        },
        headers={"X-Request-ID": "api-investigation-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "api-investigation-1"
    assert body["investigation_id"]
    assert body["route"] == "incident_investigation"
    assert body["status"] == "preliminary_diagnosis"
    assert body["investigation_plan"]
    assert body["specialist_findings"]
    assert body["evidence"]
    assert "database migration" in body["preliminary_diagnosis"]
    assert body["requires_approval"] is True


def test_investigation_workflow_produces_inc001_preliminary_diagnosis() -> None:
    response = run_investigation_workflow(
        InvestigationRequest(
            question="Why is checkout-service returning HTTP 500 after the latest deployment?",
            service_name="checkout-service",
            incident_id="INC-001",
            environment="production",
        ),
        request_id="req-inc001",
        dependencies=deps(OpsRoute.INCIDENT_INVESTIGATION),
    )

    assert response.status == "preliminary_diagnosis"
    assert response.preliminary_diagnosis is not None
    assert "shipping_region" in response.preliminary_diagnosis
    assert response.confidence is not None
    assert response.confidence > 0.8
    assert {finding["agent"] for finding in response.specialist_findings} == {
        "deployment_analysis",
        "log_analysis",
        "metrics_analysis",
        "runbook_analysis",
    }
    assert {item["source_id"] for item in response.evidence} >= {
        "log-inc001-140301",
        "metric-inc001-1404-500-rate",
        "deploy-checkout-20260714-1400",
        "rb-checkout-db-write-failures",
    }


def test_investigation_endpoint_rejects_empty_query() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/investigations",
        json={"question": "   "},
        headers={"X-Request-ID": "api-investigation-empty"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["request_id"] == "api-investigation-empty"
