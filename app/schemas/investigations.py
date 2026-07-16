from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.router import OpsRoute


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Why is checkout-service failing after the latest deployment?",
                "service_name": "checkout-service",
                "environment": "production",
            }
        }
    )

    question: str
    request_id: str | None = None
    investigation_id: str | None = None
    service_name: str | None = Field(default=None, min_length=1)
    incident_id: str | None = Field(default=None, min_length=1)
    deployment_id: str | None = Field(default=None, min_length=1)
    environment: str | None = Field(default=None, min_length=1)


class InvestigationResponse(BaseModel):
    request_id: str | None = None
    investigation_id: str
    route: OpsRoute | str
    service_name: str | None = None
    status: str
    investigation_plan: list[str] = Field(default_factory=list)
    message: str
    specialist_findings: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    preliminary_diagnosis: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    confidence: float | None = None
    requires_approval: bool = False
    approval_id: str | None = None
    approval_status: str | None = None
    approval_requested_action: str | None = None
    approval_expires_at: str | None = None
    approval_decision: str | None = None
    approval_decided_by: str | None = None
    approval_decided_at: str | None = None
    approval_result: dict | None = None
    active_agent: str | None = None
    handoff_decision: dict | None = None
    handoff_reason: str | None = None
    handoff_target: str | None = None
    handoff_timestamp: str | None = None
    specialist_result: dict | None = None


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    decided_by: str = Field(min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=500)
