import logging
import time
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.graph.approvals import (
    ApprovalStateError,
    EXPIRED,
    PENDING,
    apply_approval_decision,
    finalize_approval_response,
    is_approval_expired,
)
from app.graph.dependencies import GraphDependencies, get_graph_dependencies
from app.graph.nodes import (
    aggregate_evidence,
    assess_specialist_handoff,
    await_human_approval,
    create_investigation_plan,
    deployment_analysis_response,
    finalize_human_approval,
    general_question_response,
    generate_investigation_response,
    make_route_request_node,
    prepare_human_approval,
    report_generation_response,
    runbook_search_response,
    run_specialist_analysis,
    run_specialist_handoff,
    service_lookup_response,
    unsupported_route_response,
    validate_request,
)
from app.graph.routing import ROUTE_TO_NODE, select_route_node
from app.graph.state import InvestigationState
from app.schemas.investigations import ApprovalDecisionRequest, InvestigationRequest, InvestigationResponse

logger = logging.getLogger("opspilot.graph")


def compile_investigation_graph(dependencies: GraphDependencies | None = None):
    dependencies = dependencies or get_graph_dependencies()
    graph = StateGraph(InvestigationState)

    graph.add_node("validate_request", validate_request)
    graph.add_node("route_request", make_route_request_node(dependencies))
    graph.add_node("create_investigation_plan", create_investigation_plan)
    graph.add_node("run_specialist_analysis", run_specialist_analysis)
    graph.add_node("aggregate_evidence", aggregate_evidence)
    graph.add_node("assess_specialist_handoff", assess_specialist_handoff)
    graph.add_node("run_specialist_handoff", run_specialist_handoff)
    graph.add_node("generate_investigation_response", generate_investigation_response)
    graph.add_node("prepare_human_approval", prepare_human_approval)
    graph.add_node("await_human_approval", await_human_approval)
    graph.add_node("finalize_human_approval", finalize_human_approval)
    graph.add_node("service_lookup_response", service_lookup_response)
    graph.add_node("deployment_analysis_response", deployment_analysis_response)
    graph.add_node("runbook_search_response", runbook_search_response)
    graph.add_node("report_generation_response", report_generation_response)
    graph.add_node("general_question_response", general_question_response)
    graph.add_node("unsupported_route_response", unsupported_route_response)

    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "route_request")
    route_node_map = {node: node for node in ROUTE_TO_NODE.values()}
    route_node_map["unsupported_route_response"] = "unsupported_route_response"
    graph.add_conditional_edges("route_request", select_route_node, route_node_map)
    graph.add_edge("create_investigation_plan", "run_specialist_analysis")
    graph.add_edge("run_specialist_analysis", "aggregate_evidence")
    graph.add_edge("aggregate_evidence", "assess_specialist_handoff")
    graph.add_edge("assess_specialist_handoff", "run_specialist_handoff")
    graph.add_edge("run_specialist_handoff", "generate_investigation_response")
    graph.add_edge("generate_investigation_response", "prepare_human_approval")
    graph.add_edge("prepare_human_approval", "await_human_approval")
    graph.add_edge("await_human_approval", "finalize_human_approval")
    graph.add_edge("finalize_human_approval", END)
    graph.add_edge("service_lookup_response", END)
    graph.add_edge("deployment_analysis_response", END)
    graph.add_edge("runbook_search_response", END)
    graph.add_edge("report_generation_response", END)
    graph.add_edge("general_question_response", END)
    graph.add_edge("unsupported_route_response", END)

    return graph.compile(checkpointer=dependencies.checkpointer)


def _initial_state(payload: InvestigationRequest, request_id: str | None) -> InvestigationState:
    return {
        "request_id": request_id or payload.request_id,
        "investigation_id": payload.investigation_id or str(uuid4()),
        "user_query": payload.question,
        "service_name": payload.service_name,
        "incident_id": payload.incident_id,
        "deployment_id": payload.deployment_id,
        "environment": payload.environment,
        "route": None,
        "route_confidence": None,
        "route_reason": None,
        "fallback_used": False,
        "investigation_plan": [],
        "specialist_findings": [],
        "evidence": [],
        "preliminary_diagnosis": None,
        "recommendations": [],
        "confidence": None,
        "requires_approval": False,
        "approval_id": None,
        "approval_status": None,
        "approval_requested_action": None,
        "approval_expires_at": None,
        "approval_decision": None,
        "approval_decided_by": None,
        "approval_decided_at": None,
        "approval_result": None,
        "active_agent": None,
        "previous_active_agent": None,
        "handoff_decision": None,
        "handoff_reason": None,
        "handoff_target": None,
        "handoff_timestamp": None,
        "specialist_result": None,
        "final_response": None,
        "errors": [],
    }


def run_investigation_workflow(
    payload: InvestigationRequest,
    *,
    request_id: str | None = None,
    dependencies: GraphDependencies | None = None,
) -> InvestigationResponse:
    dependencies = dependencies or get_graph_dependencies()
    graph = compile_investigation_graph(dependencies)
    initial_state = _initial_state(payload, request_id)
    config = {"configurable": {"thread_id": initial_state["investigation_id"]}}
    started_at = time.perf_counter()
    logger.info(
        "graph_invocation_started",
        extra={
            "request_id": initial_state.get("request_id"),
            "investigation_id": initial_state.get("investigation_id"),
        },
    )
    try:
        result: dict[str, Any] = graph.invoke(initial_state, config=config)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "graph_failure",
            extra={
                "request_id": initial_state.get("request_id"),
                "investigation_id": initial_state.get("investigation_id"),
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "graph_invocation_completed",
        extra={
            "request_id": result.get("request_id"),
            "investigation_id": result.get("investigation_id"),
            "route": result.get("route"),
            "duration_ms": duration_ms,
        },
    )
    final_response = result.get("final_response")
    if not isinstance(final_response, dict):
        raise RuntimeError("Graph completed without a structured final response.")
    response = InvestigationResponse.model_validate(final_response)
    if dependencies.investigation_repository is not None:
        dependencies.investigation_repository.save_completed_investigation(
            state=result,
            response=response,
            checkpoint_thread_id=initial_state["investigation_id"],
        )
    return response


class ApprovalConflictError(RuntimeError):
    pass


class ApprovalExpiredError(RuntimeError):
    pass


def resume_investigation_approval(
    investigation_id: str,
    decision: ApprovalDecisionRequest,
    *,
    request_id: str | None = None,
    dependencies: GraphDependencies | None = None,
) -> InvestigationResponse:
    dependencies = dependencies or get_graph_dependencies()
    if dependencies.investigation_repository is None:
        raise RuntimeError("Investigation repository is not configured.")

    record = dependencies.investigation_repository.get_investigation(investigation_id)
    state = dict(record.state)
    if state.get("approval_status") != PENDING:
        raise ApprovalConflictError("Approval has already been decided or is not pending.")

    decision_data = decision.model_dump(mode="json")
    if is_approval_expired(state):
        updated_state = {
            **state,
            **apply_approval_decision(state, decision_data),
        }
        updated_state = {
            **updated_state,
            **finalize_approval_response(updated_state),
        }
        response = _response_from_state(updated_state)
        dependencies.investigation_repository.save_completed_investigation(
            state=updated_state,
            response=response,
            checkpoint_thread_id=record.checkpoint_thread_id,
        )
        dependencies.investigation_repository.record_approval_decision(
            investigation_id=investigation_id,
            request_id=request_id or record.request_id,
            approval_id=state.get("approval_id"),
            decision=decision_data["decision"],
            decided_by=decision_data["decided_by"],
            comment=decision_data.get("comment"),
            outcome=EXPIRED,
            result=updated_state.get("approval_result"),
        )
        raise ApprovalExpiredError("Approval request has expired.")

    resumed_state = _resume_with_checkpoint_if_available(
        dependencies,
        record.checkpoint_thread_id,
        decision_data,
    )
    if resumed_state is None:
        updated_state = {**state, **apply_approval_decision(state, decision_data)}
        resumed_state = {**updated_state, **finalize_approval_response(updated_state)}

    response = _response_from_state(resumed_state)
    dependencies.investigation_repository.save_completed_investigation(
        state=resumed_state,
        response=response,
        checkpoint_thread_id=record.checkpoint_thread_id,
    )
    dependencies.investigation_repository.record_approval_decision(
        investigation_id=investigation_id,
        request_id=request_id or response.request_id,
        approval_id=resumed_state.get("approval_id"),
        decision=decision_data["decision"],
        decided_by=decision_data["decided_by"],
        comment=decision_data.get("comment"),
        outcome=resumed_state.get("approval_status"),
        result=resumed_state.get("approval_result"),
    )
    return response


def _resume_with_checkpoint_if_available(
    dependencies: GraphDependencies,
    checkpoint_thread_id: str,
    decision_data: dict[str, Any],
) -> dict[str, Any] | None:
    if dependencies.checkpointer is None:
        return None
    config = {"configurable": {"thread_id": checkpoint_thread_id}}
    if dependencies.checkpointer.get_tuple(config) is None:
        return None
    graph = compile_investigation_graph(dependencies)
    try:
        result = graph.invoke(Command(resume=decision_data), config=config)
    except ApprovalStateError:
        raise
    except Exception:
        logger.exception(
            "approval_checkpoint_resume_failed",
            extra={"investigation_id": checkpoint_thread_id},
        )
        return None
    return result


def _response_from_state(state: dict[str, Any]) -> InvestigationResponse:
    final_response = state.get("final_response")
    if not isinstance(final_response, dict):
        raise RuntimeError("Graph completed without a structured final response.")
    return InvestigationResponse.model_validate(final_response)


def load_investigation_response(
    investigation_id: str,
    *,
    dependencies: GraphDependencies | None = None,
) -> InvestigationResponse:
    dependencies = dependencies or get_graph_dependencies()
    if dependencies.investigation_repository is None:
        raise RuntimeError("Investigation repository is not configured.")
    return dependencies.investigation_repository.get_response(investigation_id)
