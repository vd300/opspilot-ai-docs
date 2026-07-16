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
    approval_id: str | None
    approval_status: str | None
    approval_requested_action: str | None
    approval_expires_at: str | None
    approval_decision: str | None
    approval_decided_by: str | None
    approval_decided_at: str | None
    approval_result: dict[str, Any] | None
    active_agent: str | None
    previous_active_agent: str | None
    handoff_decision: dict[str, Any] | None
    handoff_reason: str | None
    handoff_target: str | None
    handoff_timestamp: str | None
    specialist_result: dict[str, Any] | None
    final_response: dict[str, Any] | None
    errors: list[str]
