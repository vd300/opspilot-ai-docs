import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.graph.dependencies import GraphDependencies
from app.main import create_app
from app.router import OpsRoute, RequestRouter, RouteDecision, RouterInput


class FakeClassifier:
    def __init__(self, result):
        self.result = result

    def classify(self, router_input: RouterInput):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


class FakeRouter:
    def route(self, router_input: RouterInput, *, request_id: str | None = None):
        return RouteDecision(
            route=OpsRoute.SERVICE_LOOKUP,
            service_name="checkout-service",
            service_found=True,
            confidence=0.9,
            reason="Test router selected service lookup.",
            fallback_used=True,
        )


def route(question: str, **kwargs) -> RouteDecision:
    return RequestRouter().route(RouterInput(question=question, **kwargs))


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Why is checkout-service returning HTTP 500 errors?", OpsRoute.INCIDENT_INVESTIGATION),
        ("Who owns payment-service?", OpsRoute.SERVICE_LOOKUP),
        ("What does inventory-service depend on?", OpsRoute.SERVICE_LOOKUP),
        ("Show recent deployments for payment-service.", OpsRoute.DEPLOYMENT_ANALYSIS),
        ("What changed in checkout-service v2.1.0?", OpsRoute.DEPLOYMENT_ANALYSIS),
        ("Find the checkout rollback runbook.", OpsRoute.RUNBOOK_SEARCH),
        ("Show rollback instructions for database migration failures.", OpsRoute.RUNBOOK_SEARCH),
        ("Generate a postmortem for INC-001.", OpsRoute.REPORT_GENERATION),
        ("Create an incident timeline.", OpsRoute.REPORT_GENERATION),
        ("What is FastAPI?", OpsRoute.GENERAL_QUESTION),
        ("Hello.", OpsRoute.GENERAL_QUESTION),
        ("", OpsRoute.GENERAL_QUESTION),
        ("   ", OpsRoute.GENERAL_QUESTION),
    ],
)
def test_deterministic_route_classification(question: str, expected: OpsRoute) -> None:
    assert route(question).route == expected


def test_known_service_extraction() -> None:
    decision = route("Why is checkout-service failing?")

    assert decision.service_name == "checkout-service"
    assert decision.service_found is True


def test_incident_id_extraction() -> None:
    decision = route("Generate a postmortem for inc-001.")

    assert decision.incident_id == "INC-001"


def test_deployment_version_extraction() -> None:
    decision = route("What changed in checkout-service v2.1.0?")

    assert decision.deployment_id == "v2.1.0"


def test_explicit_service_name_takes_precedence() -> None:
    decision = route("Why is checkout-service failing?", service_name="payment-service")

    assert decision.service_name == "payment-service"
    assert decision.service_found is True


def test_unknown_service_name_is_preserved_and_marked_missing() -> None:
    decision = route("Why is billing-service failing?")

    assert decision.service_name == "billing-service"
    assert decision.service_found is False
    assert "not found" in decision.reason


def test_multiple_service_names_are_preserved() -> None:
    decision = route("Compare checkout-service and payment-service errors.")

    assert decision.service_name == "checkout-service"
    assert decision.matched_services == ["checkout-service", "payment-service"]


def test_service_matching_is_case_insensitive() -> None:
    decision = route("Who owns CHECKOUT-SERVICE?")

    assert decision.service_name == "checkout-service"
    assert decision.service_found is True


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Did the latest deployment cause checkout-service to fail?", OpsRoute.INCIDENT_INVESTIGATION),
        ("Generate a report explaining why checkout-service failed.", OpsRoute.REPORT_GENERATION),
        ("Show the runbook for checkout-service failures.", OpsRoute.RUNBOOK_SEARCH),
        ("Who owns the checkout-service incident?", OpsRoute.INCIDENT_INVESTIGATION),
        ("Can you help me?", OpsRoute.GENERAL_QUESTION),
    ],
)
def test_ambiguous_requests_follow_documented_precedence(question: str, expected: OpsRoute) -> None:
    assert route(question).route == expected


def test_high_confidence_classifier_can_handle_ambiguous_general_request() -> None:
    classifier = FakeClassifier(
        {
            "route": "runbook_search",
            "service_name": None,
            "incident_id": None,
            "deployment_id": None,
            "confidence": 0.92,
            "reason": "The user is asking for a procedure.",
        }
    )
    decision = RequestRouter(classifier=classifier).route(RouterInput(question="Need assistance."))

    assert decision.route == OpsRoute.RUNBOOK_SEARCH
    assert decision.fallback_used is False


def test_classifier_cannot_invent_service_entities() -> None:
    classifier = FakeClassifier(
        {
            "route": "runbook_search",
            "service_name": "checkout recovery",
            "service_found": True,
            "matched_services": ["checkout recovery"],
            "confidence": 0.95,
            "reason": "The user is asking for a procedure.",
        }
    )

    decision = RequestRouter(classifier=classifier).route(
        RouterInput(question="I need the SOP for checkout recovery")
    )

    assert decision.route == OpsRoute.RUNBOOK_SEARCH
    assert decision.fallback_used is False
    assert decision.service_name is None
    assert decision.service_found is None
    assert decision.matched_services == []


@pytest.mark.parametrize(
    ("classifier_result", "failure_type"),
    [
        (TimeoutError("timeout"), "timeout"),
        ({"route": "service_lookup"}, "schema_validation"),
        ({"route": "unsupported", "confidence": 0.9, "reason": "bad"}, "schema_validation"),
        ({"route": "service_lookup", "confidence": 1.5, "reason": "bad"}, "schema_validation"),
        ({"route": "service_lookup", "confidence": 0.2, "reason": "low"}, "low_confidence"),
        (RuntimeError("provider down"), "provider_error"),
    ],
)
def test_classifier_failures_fall_back_deterministically(classifier_result, failure_type: str) -> None:
    classifier = FakeClassifier(classifier_result)
    decision = RequestRouter(classifier=classifier).route(
        RouterInput(question="Who owns checkout-service?")
    )

    assert decision.route == OpsRoute.SERVICE_LOOKUP
    assert decision.fallback_used is True
    assert decision.classification_failure_type == failure_type


def test_obvious_supported_pattern_overrides_classifier() -> None:
    classifier = FakeClassifier(
        {
            "route": "general_question",
            "confidence": 0.99,
            "reason": "Incorrect but valid structured output.",
        }
    )

    decision = RequestRouter(classifier=classifier).route(
        RouterInput(question="Why is checkout-service failing?")
    )

    assert decision.route == OpsRoute.INCIDENT_INVESTIGATION
    assert decision.fallback_used is True
    assert decision.classification_failure_type == "obvious_pattern"


def test_router_logs_structured_decision_fields(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="opspilot.router"):
        RequestRouter().route(RouterInput(question="Who owns checkout-service?"), request_id="req-123")

    record = next(item for item in caplog.records if item.message == "route_selected")
    assert record.request_id == "req-123"
    assert record.route == "service_lookup"
    assert record.fallback_used is True
    assert record.classification_failure_type == "provider_error"


def test_router_evaluation_fixture_exists() -> None:
    assert Path("tests/fixtures/router_evaluation.json").exists()


def test_router_classify_endpoint_preserves_request_id() -> None:
    client = TestClient(create_app(graph_dependencies=GraphDependencies(router=FakeRouter())))  # type: ignore[arg-type]

    response = client.post(
        "/api/v1/router/classify",
        json={"question": "Who owns checkout-service?"},
        headers={"X-Request-ID": "router-req-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "router-req-1"
    assert response.json()["route"] == "service_lookup"
