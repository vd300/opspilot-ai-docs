from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Environment = Literal["production", "staging", "local"]
HealthStatus = Literal["healthy", "degraded", "unhealthy", "not_applicable"]
DependencyKind = Literal["http", "database", "event", "internal"]
DeploymentStatus = Literal["succeeded", "failed", "rolled_back"]
ChangeKind = Literal["application", "database_migration", "configuration"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
MetricName = Literal[
    "http_500_rate_percent",
    "request_rate_per_minute",
    "p95_latency_ms",
    "database_insert_errors_per_minute",
]
EvidenceType = Literal["deployment", "log", "metric", "runbook", "service", "dependency"]


class TimezoneAwareModel(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def validate_timezone_aware_datetimes(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("datetime fields must include timezone information")
        return value


class ServiceOwner(BaseModel):
    owner_id: str
    team_name: str
    contact_email: str
    escalation_channel: str


class ServiceCatalogEntry(BaseModel):
    service_name: str
    description: str
    owner_id: str
    repository_name: str
    environment: Environment
    health_status: HealthStatus


class ServiceDependency(BaseModel):
    dependency_id: str
    source_service: str
    target_service: str
    dependency_type: DependencyKind
    description: str
    required: bool = True


class LogEvent(TimezoneAwareModel):
    event_id: str
    timestamp: datetime
    service_name: str
    environment: Environment
    level: LogLevel
    message: str
    component: str
    trace_id: str | None = None
    error_code: str | None = None
    fields: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class MetricSnapshot(TimezoneAwareModel):
    metric_id: str
    timestamp: datetime
    service_name: str
    environment: Environment
    metric_name: MetricName
    value: float
    unit: str
    labels: dict[str, str] = Field(default_factory=dict)


class DeploymentChange(BaseModel):
    change_id: str
    change_type: ChangeKind
    description: str
    path: str
    risk_level: Literal["low", "medium", "high"]


class DeploymentRecord(TimezoneAwareModel):
    deployment_id: str
    service_name: str
    environment: Environment
    version: str
    deployed_at: datetime
    deployed_by: str
    status: DeploymentStatus
    pipeline_url: str
    changes: list[DeploymentChange]


class RunbookStep(BaseModel):
    step_id: str
    title: str
    action: str
    requires_approval: bool


class Runbook(BaseModel):
    runbook_id: str
    title: str
    service_names: list[str]
    summary: str
    symptoms: list[str]
    steps: list[RunbookStep]
    related_evidence_types: list[EvidenceType]


class EvidenceReference(BaseModel):
    evidence_id: str
    evidence_type: EvidenceType
    source_id: str
    description: str


class IncidentScenario(TimezoneAwareModel):
    incident_id: str
    title: str
    environment: Environment
    service_name: str
    starts_at: datetime
    evidence: list[EvidenceReference]
    related_services: list[str]
    related_runbook_ids: list[str]

