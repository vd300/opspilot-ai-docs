from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    request_id: str
    investigation_id: str
    user_query: str
    service_name: str | None
    incident_id: str | None
    deployment_id: str | None
    environment: str | None
    route: str | None
    route_confidence: float | None
    route_reason: str | None
    fallback_used: bool
    investigation_plan: list[str]
    specialist_findings: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    preliminary_diagnosis: str | None
    recommendations: list[str]
    confidence: float | None
    requires_approval: bool
    active_agent: str | None
    final_response: dict[str, Any] | None
    errors: list[str]
