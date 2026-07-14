from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpsRoute(StrEnum):
    INCIDENT_INVESTIGATION = "incident_investigation"
    SERVICE_LOOKUP = "service_lookup"
    DEPLOYMENT_ANALYSIS = "deployment_analysis"
    RUNBOOK_SEARCH = "runbook_search"
    REPORT_GENERATION = "report_generation"
    GENERAL_QUESTION = "general_question"


class RouterInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Why is checkout-service returning HTTP 500 errors?",
                "conversation_context": [],
                "service_name": None,
                "incident_id": None,
            }
        }
    )

    question: str
    conversation_context: list[str] = Field(default_factory=list)
    service_name: str | None = Field(default=None, min_length=1)
    incident_id: str | None = Field(default=None, min_length=1)


class RouteDecision(BaseModel):
    route: OpsRoute
    service_name: str | None = None
    service_found: bool | None = None
    matched_services: list[str] = Field(default_factory=list)
    incident_id: str | None = None
    deployment_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    fallback_used: bool = False
    classification_failure_type: str | None = None

    @field_validator("incident_id")
    @classmethod
    def normalize_incident_id(cls, value: str | None) -> str | None:
        return value.upper() if value else value
