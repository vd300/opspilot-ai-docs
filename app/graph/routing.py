from app.graph.state import InvestigationState
from app.router import OpsRoute


ROUTE_TO_NODE = {
    OpsRoute.INCIDENT_INVESTIGATION.value: "create_investigation_plan",
    OpsRoute.SERVICE_LOOKUP.value: "service_lookup_response",
    OpsRoute.DEPLOYMENT_ANALYSIS.value: "deployment_analysis_response",
    OpsRoute.RUNBOOK_SEARCH.value: "runbook_search_response",
    OpsRoute.REPORT_GENERATION.value: "report_generation_response",
    OpsRoute.GENERAL_QUESTION.value: "general_question_response",
}


def select_route_node(state: InvestigationState) -> str:
    route = state.get("route")
    if route in ROUTE_TO_NODE:
        return ROUTE_TO_NODE[route]
    return "unsupported_route_response"
