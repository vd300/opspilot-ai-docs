import logging
import time
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.dependencies import GraphDependencies, get_graph_dependencies
from app.graph.nodes import (
    aggregate_evidence,
    assess_specialist_handoff,
    create_investigation_plan,
    deployment_analysis_response,
    general_question_response,
    generate_investigation_response,
    make_route_request_node,
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
from app.schemas.investigations import InvestigationRequest, InvestigationResponse

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
    graph.add_edge("generate_investigation_response", END)
    graph.add_edge("service_lookup_response", END)
    graph.add_edge("deployment_analysis_response", END)
    graph.add_edge("runbook_search_response", END)
    graph.add_edge("report_generation_response", END)
    graph.add_edge("general_question_response", END)
    graph.add_edge("unsupported_route_response", END)

    return graph.compile()


def _initial_state(payload: InvestigationRequest, request_id: str | None) -> InvestigationState:
    return {
        "request_id": request_id or payload.request_id,
        "investigation_id": payload.investigation_id,
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
    graph = compile_investigation_graph(dependencies)
    initial_state = _initial_state(payload, request_id)
    started_at = time.perf_counter()
    logger.info(
        "graph_invocation_started",
        extra={
            "request_id": initial_state.get("request_id"),
            "investigation_id": initial_state.get("investigation_id"),
        },
    )
    try:
        result: dict[str, Any] = graph.invoke(initial_state)
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
    return InvestigationResponse.model_validate(final_response)
