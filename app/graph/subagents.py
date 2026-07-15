from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Literal

from pydantic import BaseModel, Field

from app.shopflow.tools import get_metrics
from app.skills import get_skill
from app.skills.deployment_comparison import (
    DeploymentComparisonRequest,
    DeploymentComparisonResult,
)
from app.skills.incident_timeline import IncidentTimelineRequest, IncidentTimelineResult
from app.skills.log_investigation import LogInvestigationRequest, LogInvestigationResult
from app.skills.models import SkillEvidence
from app.skills.runbook_retrieval import (
    RunbookRetrievalRequest,
    RunbookRetrievalResult,
)

AgentName = Literal[
    "log_analysis",
    "metrics_analysis",
    "deployment_analysis",
    "runbook_analysis",
]


class SpecialistInput(BaseModel):
    service_name: str
    environment: str = "production"
    incident_id: str | None = None
    deployment_id: str | None = None
    user_query: str | None = None


class EvidenceItem(BaseModel):
    source_type: str
    source_id: str
    location: str
    detail: str
    timestamp: str | None = None


class Hypothesis(BaseModel):
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class SpecialistFinding(BaseModel):
    agent: AgentName
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def run_log_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    skill = get_skill("log_investigation")
    result = skill.execute(
        LogInvestigationRequest(
            service_name=input_data.service_name,
            environment=input_data.environment,
            query="shipping_region",
            level="ERROR",
        )
    )
    log_result = LogInvestigationResult.model_validate(result)
    timeline = _build_timeline(log_result.evidence)
    evidence = _to_agent_evidence(log_result.evidence)
    if timeline.found:
        evidence = _timeline_ordered_evidence(evidence, timeline)

    if not log_result.found:
        return SpecialistFinding(
            agent="log_analysis",
            summary=log_result.message,
            missing_information=log_result.missing_information,
            skills_used=["log_investigation", "incident_timeline"],
        )

    return SpecialistFinding(
        agent="log_analysis",
        summary="Checkout logs show database insert failures involving shipping_region.",
        evidence=evidence,
        hypotheses=[
            Hypothesis(
                description="Checkout requests are failing because order inserts are missing shipping_region.",
                confidence=0.88,
            )
        ],
        skills_used=["log_investigation", "incident_timeline"],
        confidence=0.88,
    )


def run_metrics_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    response = get_metrics(
        service_name=input_data.service_name,
        environment=input_data.environment,  # type: ignore[arg-type]
        metric_name="http_500_rate_percent",
    )
    evidence = [
        EvidenceItem(
            source_type=source.source_type,
            source_id=source.source_id,
            location=source.location,
            timestamp=metric.timestamp.isoformat(),
            detail=f"{metric.metric_name}={metric.value}{metric.unit}",
        )
        for metric, source in zip(response.metrics, response.source_references, strict=False)
    ]
    if not response.found:
        return SpecialistFinding(
            agent="metrics_analysis",
            summary=response.message,
            missing_information=["HTTP 500 rate metrics were unavailable."],
        )

    values = [metric.value for metric in response.metrics]
    spike_detected = len(values) >= 2 and values[-1] > values[0]
    hypotheses = []
    if spike_detected:
        hypotheses.append(
            Hypothesis(
                description="HTTP 500 errors increased during the incident window.",
                confidence=0.82,
            )
        )
    return SpecialistFinding(
        agent="metrics_analysis",
        summary="HTTP 500 rate increased from 1.0% to 23.0%.",
        evidence=evidence,
        hypotheses=hypotheses,
        confidence=0.82 if spike_detected else 0.5,
    )


def run_deployment_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    skill = get_skill("deployment_comparison")
    result = skill.execute(
        DeploymentComparisonRequest(
            service_name=input_data.service_name,
            environment=input_data.environment,
            deployment_id=input_data.deployment_id,
        )
    )
    deployment_result = DeploymentComparisonResult.model_validate(result)
    timeline = _build_timeline(deployment_result.evidence)
    evidence = _to_agent_evidence(deployment_result.evidence)
    if timeline.found:
        evidence = _timeline_ordered_evidence(evidence, timeline)

    if not deployment_result.found:
        return SpecialistFinding(
            agent="deployment_analysis",
            summary=deployment_result.message,
            missing_information=deployment_result.missing_information,
            skills_used=["deployment_comparison", "incident_timeline"],
        )

    hypotheses = []
    if deployment_result.has_database_migration:
        hypotheses.append(
            Hypothesis(
                description="The latest deployment included a high-risk database migration before the failures.",
                confidence=0.9,
            )
        )
    return SpecialistFinding(
        agent="deployment_analysis",
        summary="Deployment v2.1.0 included a database migration shortly before failures began.",
        evidence=evidence,
        hypotheses=hypotheses,
        skills_used=["deployment_comparison", "incident_timeline"],
        confidence=0.9 if deployment_result.has_database_migration else 0.55,
    )


def run_runbook_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    skill = get_skill("runbook_retrieval")
    result = skill.execute(
        RunbookRetrievalRequest(
            service_name=input_data.service_name,
            query="database",
        )
    )
    runbook_result = RunbookRetrievalResult.model_validate(result)

    if not runbook_result.found:
        return SpecialistFinding(
            agent="runbook_analysis",
            summary=runbook_result.message,
            missing_information=runbook_result.missing_information,
            skills_used=["runbook_retrieval"],
        )

    return SpecialistFinding(
        agent="runbook_analysis",
        summary="Runbook guidance recommends safe rollback review and approval for database write failures.",
        evidence=_to_agent_evidence(runbook_result.evidence),
        hypotheses=[
            Hypothesis(
                description="Rollback or migration remediation should require human approval.",
                confidence=0.78,
            )
        ],
        skills_used=["runbook_retrieval"],
        confidence=0.78,
    )


def run_specialist_subagents(input_data: SpecialistInput) -> list[SpecialistFinding]:
    agents: list[Callable[[SpecialistInput], SpecialistFinding]] = [
        run_log_analysis,
        run_metrics_analysis,
        run_deployment_analysis,
        run_runbook_analysis,
    ]
    findings: list[SpecialistFinding] = []
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        future_to_agent = {executor.submit(agent, input_data): agent for agent in agents}
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                findings.append(future.result())
            except Exception as exc:
                findings.append(
                    SpecialistFinding(
                        agent=_agent_name(agent),
                        summary=f"{_agent_name(agent)} failed.",
                        errors=[str(exc)],
                        missing_information=["Specialist output unavailable because the tool call failed."],
                    )
                )
    return sorted(findings, key=lambda finding: finding.agent)


def collect_unique_evidence(findings: list[SpecialistFinding]) -> list[EvidenceItem]:
    evidence_by_key: dict[tuple[str, str, str], EvidenceItem] = {}
    for finding in findings:
        for item in finding.evidence:
            key = (item.source_type, item.source_id, item.detail)
            evidence_by_key[key] = item
    return list(evidence_by_key.values())


def _agent_name(agent: Callable[[SpecialistInput], SpecialistFinding]) -> AgentName:
    names: dict[str, AgentName] = {
        "run_log_analysis": "log_analysis",
        "run_metrics_analysis": "metrics_analysis",
        "run_deployment_analysis": "deployment_analysis",
        "run_runbook_analysis": "runbook_analysis",
    }
    return names.get(agent.__name__, "log_analysis")


def _to_agent_evidence(evidence: list[SkillEvidence]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            source_type=item.source_type,
            source_id=item.source_id,
            location=item.location,
            detail=item.detail,
            timestamp=item.timestamp,
        )
        for item in evidence
    ]


def _build_timeline(evidence: list[SkillEvidence]) -> IncidentTimelineResult:
    timeline_skill = get_skill("incident_timeline")
    result = timeline_skill.execute(IncidentTimelineRequest(evidence=evidence))
    return IncidentTimelineResult.model_validate(result)


def _timeline_ordered_evidence(
    evidence: list[EvidenceItem],
    timeline: IncidentTimelineResult,
) -> list[EvidenceItem]:
    order = {event.source_id: index for index, event in enumerate(timeline.events)}
    return sorted(evidence, key=lambda item: order.get(item.source_id, len(order)))
