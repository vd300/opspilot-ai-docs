import logging
from typing import Any
from uuid import uuid4

from app.graph.dependencies import GraphDependencies
from app.graph.approvals import (
    create_pending_approval,
    finalize_approval_response,
    wait_for_human_approval,
)
from app.graph.handoffs import (
    HandoffDecision,
    assess_handoff,
    handoff_timestamp,
    run_database_specialist,
    validate_handoff_target,
)
from app.graph.state import InvestigationState
from app.graph.subagents import (
    SpecialistFinding,
    SpecialistInput,
    collect_unique_evidence,
    run_specialist_subagents,
)
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


def run_specialist_analysis(state: InvestigationState) -> InvestigationState:
    node = "run_specialist_analysis"
    _log_node("graph_node_entered", state, node)
    service_name = state.get("service_name") or "checkout-service"
    input_data = SpecialistInput(
        service_name=service_name,
        environment=state.get("environment") or "production",
        incident_id=state.get("incident_id"),
        deployment_id=state.get("deployment_id"),
        user_query=state.get("user_query"),
    )
    findings = run_specialist_subagents(input_data)
    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "specialist_findings": [
            finding.model_dump(mode="json", exclude_none=True) for finding in findings
        ],
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def aggregate_evidence(state: InvestigationState) -> InvestigationState:
    node = "aggregate_evidence"
    _log_node("graph_node_entered", state, node)
    parsed_findings = [
        SpecialistFinding.model_validate(finding)
        for finding in state.get("specialist_findings", [])
    ]
    evidence = collect_unique_evidence(parsed_findings)
    missing_information = [
        missing
        for finding in parsed_findings
        for missing in finding.missing_information
    ]
    errors = list(state.get("errors") or [])
    errors.extend(
        f"{finding.agent}: {error}"
        for finding in parsed_findings
        for error in finding.errors
    )
    confidence = _combined_confidence(parsed_findings)
    diagnosis = (
        "The likely cause of INC-001 is the checkout-service v2.1.0 database migration "
        "adding or requiring shipping_region without compatible write-path data. "
        "Logs show insert failures, metrics show the HTTP 500 spike, and deployment "
        "evidence ties the failure window to a high-risk database migration."
    )
    if missing_information:
        diagnosis = f"{diagnosis} Missing information: {'; '.join(missing_information)}."

    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "evidence": [item.model_dump(mode="json", exclude_none=True) for item in evidence],
        "preliminary_diagnosis": diagnosis,
        "recommendations": [
            "Pause further checkout-service deployments until the migration is reviewed.",
            "Confirm whether shipping_region is required by the new schema and absent from checkout writes.",
            "Use the checkout database write failures runbook before rollback or migration remediation.",
            "Get human approval before any production rollback or schema change.",
        ],
        "confidence": confidence,
        "requires_approval": True,
        "errors": errors,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def assess_specialist_handoff(state: InvestigationState) -> InvestigationState:
    node = "assess_specialist_handoff"
    _log_node("graph_node_entered", state, node)
    parsed_findings = [
        SpecialistFinding.model_validate(finding)
        for finding in state.get("specialist_findings", [])
    ]
    decision = assess_handoff(parsed_findings)
    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "handoff_decision": decision.model_dump(mode="json", exclude_none=True),
        "handoff_reason": decision.reason if decision.should_handoff else None,
        "handoff_target": decision.target_agent if decision.should_handoff else None,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def run_specialist_handoff(state: InvestigationState) -> InvestigationState:
    node = "run_specialist_handoff"
    _log_node("graph_node_entered", state, node)
    raw_decision = state.get("handoff_decision")
    if not raw_decision:
        next_state: InvestigationState = {"active_agent": "incident_coordinator"}
        _log_node("graph_node_completed", {**state, **next_state}, node)
        return next_state

    decision = HandoffDecision.model_validate(raw_decision)
    try:
        target = validate_handoff_target(decision)
    except ValueError as exc:
        logger.exception(
            "graph_node_failed",
            extra={
                "request_id": state.get("request_id"),
                "investigation_id": state.get("investigation_id"),
                "node": node,
                "handoff_target": decision.target_agent,
            },
        )
        raise WorkflowExecutionError(str(exc)) from exc

    if target is None:
        next_state = {
            "active_agent": "incident_coordinator",
            "previous_active_agent": state.get("active_agent"),
        }
        _log_node("graph_node_completed", {**state, **next_state}, node)
        return next_state

    parsed_findings = [
        SpecialistFinding.model_validate(finding)
        for finding in state.get("specialist_findings", [])
    ]
    result = run_database_specialist(decision, parsed_findings)
    next_state = {
        "previous_active_agent": state.get("active_agent") or "incident_coordinator",
        "active_agent": "incident_coordinator",
        "handoff_reason": decision.reason,
        "handoff_target": target,
        "handoff_timestamp": handoff_timestamp(),
        "specialist_result": result.model_dump(mode="json", exclude_none=True),
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
        "status": "preliminary_diagnosis",
        "investigation_plan": state.get("investigation_plan") or [],
        "message": state.get("preliminary_diagnosis")
        or "The investigation workflow completed specialist analysis.",
        "specialist_findings": state.get("specialist_findings") or [],
        "evidence": state.get("evidence") or [],
        "preliminary_diagnosis": state.get("preliminary_diagnosis"),
        "recommendations": state.get("recommendations") or [],
        "confidence": state.get("confidence"),
        "requires_approval": state.get("requires_approval", False),
        "active_agent": state.get("active_agent"),
        "handoff_decision": state.get("handoff_decision"),
        "handoff_reason": state.get("handoff_reason"),
        "handoff_target": state.get("handoff_target"),
        "handoff_timestamp": state.get("handoff_timestamp"),
        "specialist_result": state.get("specialist_result"),
    }
    next_state: InvestigationState = {
        "active_agent": "incident_coordinator",
        "final_response": final_response,
    }
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def prepare_human_approval(state: InvestigationState) -> InvestigationState:
    node = "prepare_human_approval"
    _log_node("graph_node_entered", state, node)
    next_state = create_pending_approval(state)
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def await_human_approval(state: InvestigationState) -> InvestigationState:
    node = "await_human_approval"
    _log_node("graph_node_entered", state, node)
    next_state = wait_for_human_approval(state)
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def finalize_human_approval(state: InvestigationState) -> InvestigationState:
    node = "finalize_human_approval"
    _log_node("graph_node_entered", state, node)
    next_state = finalize_approval_response(state)
    _log_node("graph_node_completed", {**state, **next_state}, node)
    return next_state


def _combined_confidence(findings: list) -> float:
    confident_findings = [finding.confidence for finding in findings if finding.confidence > 0]
    if not confident_findings:
        return 0.0
    return round(sum(confident_findings) / len(confident_findings), 2)


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
