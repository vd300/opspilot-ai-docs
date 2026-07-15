from pydantic import Field

from app.shopflow.tools import search_logs
from app.shopflow.tools.schemas import LogSearchResponse
from app.skills.contracts import SkillRequest, SkillResult
from app.skills.models import SkillEvidence


class LogInvestigationRequest(SkillRequest):
    service_name: str = Field(min_length=1)
    environment: str = "production"
    query: str = Field(default="shipping_region", min_length=1)
    level: str = "ERROR"


class LogInvestigationResult(SkillResult):
    skill_name: str = "log_investigation"
    logs: list[dict] = Field(default_factory=list)
    evidence: list[SkillEvidence] = Field(default_factory=list)
    first_failure_timestamp: str | None = None


class LogInvestigationSkill:
    name = "log_investigation"

    def execute(self, request: LogInvestigationRequest) -> LogInvestigationResult:
        response = search_logs(
            service_name=request.service_name,
            environment=request.environment,  # type: ignore[arg-type]
            query=request.query,
            level=request.level,
        )
        return _build_result(response)


def _build_result(response: LogSearchResponse) -> LogInvestigationResult:
    evidence = [
        SkillEvidence(
            source_type=source.source_type,
            source_id=source.source_id,
            location=source.location,
            timestamp=log.timestamp.isoformat(),
            detail=f"{log.level} in {log.component}: {log.message}",
        )
        for log, source in zip(response.logs, response.source_references, strict=False)
    ]
    return LogInvestigationResult(
        found=response.found,
        message=response.message,
        logs=[log.model_dump(mode="json") for log in response.logs],
        evidence=evidence,
        first_failure_timestamp=evidence[0].timestamp if evidence else None,
        missing_information=[] if response.found else ["No matching checkout database write errors were found."],
    )
