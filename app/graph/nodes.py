import logging
from typing import Any
from uuid import uuid4

from app.graph.dependencies import GraphDependencies
from app.graph.state import InvestigationState
from app.router import OpsRoute, RouterInput

logger = logging.getLogger("opspilot.graph")

SUPPORTED_ENVIRONMENTS = {"production", "staging", "development", "local"}


class WorkflowValidationError(ValueError):
    pass


class WorkflowExecutionError(RuntimeError):
    pass


def _log_node(message: str, state: InvestigationState, node: str) -> None:
    logger.info(
        message,
        extra={
            "request_id": state.get("request_id"),
            "investigation_id": state.get("investigation_id"),
            "node": node,
            "route": state.get("route"),
            "active_agent": state.get("active_agent"),
        },
    )


def _normalize_optional(value: str | None, *, lower: bool = False, upper: bool = False) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if lower:
        return stripped.lower()
    if upper:
        return stripped.upper()
    return stripped


def validate_request(state: InvestigationState) -> InvestigationState:
    node = "validate_request"
    _log_node("graph_node_entered", state, node)

    errors = list(state.get("errors") or [])
    user_query = (state.get("user_query") or "").strip()
    if not user_query:
        errors.append("User query must not be empty.")
        next_state: InvestigationState = {"errors": errors}
        _log_node("graph_node_failed", {**state, **next_state}, node)
        raise WorkflowValidationError("User query must not be empty.")

    environment = _normalize_optional(state.get("environment"), lower=True)
    if environment and environment not in SUPPORTED_ENVIRONMENTS:
        errors.append(f"Unsupported environment: {environment}.")
        next_state = {"errors": errors}
        _log_node("graph_node_failed", {**state, **next_state}, node)
        raise WorkflowValidationError(f"Unsupported environment: {environment}.")

    next_state = {
        "investigation_id": state.get("investigation_id") or str(uuid4()),
        "user_query": user_query,
        "service_name": _normalize_optional(state.get("service_name"), lower=True),
        "incident_id": _normalize_optional(state.get("incident_id"), upper=True),
        "deployment_id": _normalize_optional(state.get("deployment_id")),
        "environment": environment,
        "errors": errors,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def make_route_request_node(dependencies: GraphDependencies):
    def route_request(state: InvestigationState) -> InvestigationState:
        node = "route_request"
        _log_node("graph_node_entered", state, node)
        try:
            decision = dependencies.router.route(
                RouterInput(
                    question=state["user_query"],
                    service_name=state.get("service_name"),
                    incident_id=state.get("incident_id"),
                ),
                request_id=state.get("request_id"),
            )
        except Exception as exc:
            logger.exception(
                "graph_node_failed",
                extra={
                    "request_id": state.get("request_id"),
                    "investigation_id": state.get("investigation_id"),
                    "node": node,
                },
            )
            raise WorkflowExecutionError("Router failed during graph execution.") from exc

        next_state: InvestigationState = {
            "route": decision.route.value,
            "route_confidence": decision.confidence,
            "route_reason": decision.reason,
            "fallback_used": decision.fallback_used,
            "service_name": decision.service_name or state.get("service_name"),
            "incident_id": decision.incident_id or state.get("incident_id"),
            "deployment_id": decision.deployment_id or state.get("deployment_id"),
            "active_agent": "request_router",
        }
        _log_node("graph_node_completed", {**state, **next_state}, node)
        return next_state

    return route_request


def create_investigation_plan(state: InvestigationState) -> InvestigationState:
    node = "create_investigation_plan"
    _log_node("graph_node_entered", state, node)
    plan = [
        "Review recent service logs.",
        "Review relevant service metrics.",
        "Review recent deployments.",
        "Search relevant runbooks.",
        "Compare evidence and determine next steps.",
    ]
    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "investigation_plan": plan,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def generate_investigation_response(state: InvestigationState) -> InvestigationState:
    node = "generate_investigation_response"
    _log_node("graph_node_entered", state, node)
    final_response = {
        "request_id": state.get("request_id"),
        "investigation_id": state.get("investigation_id"),
        "route": OpsRoute.INCIDENT_INVESTIGATION.value,
        "service_name": state.get("service_name"),
        "status": "planned",
        "investigation_plan": state.get("investigation_plan") or [],
        "message": (
            "The investigation workflow has been created. "
            "Specialist analysis will be implemented in Phase 6."
        ),
    }
    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "final_response": final_response,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def _temporary_response(
    state: InvestigationState,
    *,
    node: str,
    active_agent: str,
    status: str,
    message: str,
) -> InvestigationState:
    _log_node("graph_node_entered", state, node)
    final_response: dict[str, Any] = {
        "request_id": state.get("request_id"),
        "investigation_id": state.get("investigation_id"),
        "route": state.get("route"),
        "service_name": state.get("service_name"),
        "status": status,
        "investigation_plan": state.get("investigation_plan") or [],
        "message": message,
    }
    next_state: InvestigationState = {
        "active_agent": active_agent,
        "final_response": final_response,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def service_lookup_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="service_lookup_response",
        active_agent="service_lookup_workflow",
        status="selected",
        message=(
            "The service lookup route was selected. "
            "Detailed service execution will be added in a later phase."
        ),
    )


def deployment_analysis_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="deployment_analysis_response",
        active_agent="deployment_analysis_workflow",
        status="selected",
        message=(
            "The deployment analysis workflow was selected. "
            "Detailed deployment analysis will be added in a later phase."
        ),
    )


def runbook_search_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="runbook_search_response",
        active_agent="runbook_search_workflow",
        status="selected",
        message=(
            "The runbook search workflow was selected. "
            "Runbook retrieval will be added in a later phase."
        ),
    )


def report_generation_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="report_generation_response",
        active_agent="report_generation_workflow",
        status="selected",
        message=(
            "The report generation workflow was selected. "
            "Incident report generation will be added in a later phase."
        ),
    )


def general_question_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="general_question_response",
        active_agent="general_question_workflow",
        status="selected",
        message="The request was classified as a general question.",
    )


def unsupported_route_response(state: InvestigationState) -> InvestigationState:
    return _temporary_response(
        state,
        node="unsupported_route_response",
        active_agent="general_question_workflow",
        status="unsupported_route",
        message="The selected route is not supported by the Phase 5 workflow.",
    )
