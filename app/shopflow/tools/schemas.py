from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.shopflow.models import (
    DeploymentChange,
    DeploymentRecord,
    Environment,
    EvidenceType,
    LogEvent,
    LogLevel,
    MetricName,
    MetricSnapshot,
    Runbook,
    ServiceCatalogEntry,
    ServiceDependency,
    ServiceOwner,
)


class ToolInput(BaseModel):
    @field_validator("*", mode="after")
    @classmethod
    def validate_timezone_aware_datetimes(cls, value):
        if isinstance(value, datetime) and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("datetime filters must include timezone information")
        return value


class TimeWindowInput(ToolInput):
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_time_window(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be before or equal to end_time")
        return self


class SourceReference(BaseModel):
    source_type: EvidenceType
    source_id: str
    location: str


class ToolResponse(BaseModel):
    found: bool
    message: str
    source_references: list[SourceReference] = Field(default_factory=list)


class SearchLogsInput(TimeWindowInput):
    service_name: str = Field(min_length=1)
    environment: Environment = "production"
    query: str | None = Field(default=None, min_length=1)
    level: LogLevel | None = None
    limit: int = Field(default=50, ge=1, le=100)


class LogSearchResponse(ToolResponse):
    logs: list[LogEvent] = Field(default_factory=list)


class GetMetricsInput(TimeWindowInput):
    service_name: str = Field(min_length=1)
    environment: Environment = "production"
    metric_name: MetricName | None = None
    limit: int = Field(default=50, ge=1, le=100)


class MetricSearchResponse(ToolResponse):
    metrics: list[MetricSnapshot] = Field(default_factory=list)


class GetRecentDeploymentsInput(ToolInput):
    service_name: str = Field(min_length=1)
    environment: Environment = "production"
    since: datetime | None = None
    limit: int = Field(default=10, ge=1, le=50)


class DeploymentSearchResponse(ToolResponse):
    deployments: list[DeploymentRecord] = Field(default_factory=list)


class GetDeploymentDiffInput(ToolInput):
    deployment_id: str = Field(min_length=1)


class DeploymentDiffResponse(ToolResponse):
    deployment: DeploymentRecord | None = None
    changes: list[DeploymentChange] = Field(default_factory=list)


class SearchRunbooksInput(ToolInput):
    query: str | None = Field(default=None, min_length=1)
    service_name: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_query_or_service(self):
        if not self.query and not self.service_name:
            raise ValueError("query or service_name is required")
        return self


class RunbookSearchResponse(ToolResponse):
    runbooks: list[Runbook] = Field(default_factory=list)


class GetServiceOwnerInput(ToolInput):
    service_name: str = Field(min_length=1)
    environment: Environment = "production"


class OwnerLookupResponse(ToolResponse):
    service: ServiceCatalogEntry | None = None
    owner: ServiceOwner | None = None


class GetServiceDependenciesInput(ToolInput):
    service_name: str = Field(min_length=1)
    environment: Environment = "production"
    direction: Literal["outbound", "inbound", "both"] = "outbound"


class DependencyLookupResponse(ToolResponse):
    service: ServiceCatalogEntry | None = None
    dependencies: list[ServiceDependency] = Field(default_factory=list)
