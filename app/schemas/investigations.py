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
