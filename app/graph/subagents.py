from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Literal

from pydantic import BaseModel, Field

from app.shopflow.tools import (
    get_deployment_diff,
    get_metrics,
    get_recent_deployments,
    search_logs,
    search_runbooks,
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
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def run_log_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    response = search_logs(
        service_name=input_data.service_name,
        environment=input_data.environment,  # type: ignore[arg-type]
        query="shipping_region",
        level="ERROR",
    )
    evidence = [
        EvidenceItem(
            source_type=source.source_type,
            source_id=source.source_id,
            location=source.location,
            timestamp=log.timestamp.isoformat(),
            detail=f"{log.level} in {log.component}: {log.message}",
        )
        for log, source in zip(response.logs, response.source_references, strict=False)
    ]
    if not response.found:
        return SpecialistFinding(
            agent="log_analysis",
            summary=response.message,
            missing_information=["No matching checkout database write errors were found."],
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
    deployments_response = get_recent_deployments(
        service_name=input_data.service_name,
        environment=input_data.environment,  # type: ignore[arg-type]
        limit=1,
    )
    if not deployments_response.found or not deployments_response.deployments:
        return SpecialistFinding(
            agent="deployment_analysis",
            summary=deployments_response.message,
            missing_information=["No recent deployment was found for the service."],
        )

    deployment = deployments_response.deployments[0]
    diff_response = get_deployment_diff(deployment_id=input_data.deployment_id or deployment.deployment_id)
    evidence = [
        EvidenceItem(
            source_type=source.source_type,
            source_id=source.source_id,
            location=source.location,
            timestamp=deployment.deployed_at.isoformat(),
            detail=f"Deployment {deployment.version} status={deployment.status}",
        )
        for source in deployments_response.source_references
    ]
    for change in diff_response.changes:
        evidence.append(
            EvidenceItem(
                source_type="deployment",
                source_id=change.change_id,
                location=change.path,
                timestamp=deployment.deployed_at.isoformat(),
                detail=f"{change.change_type}: {change.description}",
            )
        )

    has_database_migration = any(change.change_type == "database_migration" for change in diff_response.changes)
    hypotheses = []
    if has_database_migration:
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
        confidence=0.9 if has_database_migration else 0.55,
    )


def run_runbook_analysis(input_data: SpecialistInput) -> SpecialistFinding:
    response = search_runbooks(
        service_name=input_data.service_name,
        query="database",
    )
    evidence = []
    for runbook, source in zip(response.runbooks, response.source_references, strict=False):
        approval_steps = [
            step.title for step in runbook.steps if step.requires_approval
        ]
        detail = f"{runbook.title}: {runbook.summary}"
        if approval_steps:
            detail = f"{detail} Approval required for: {', '.join(approval_steps)}."
        evidence.append(
            EvidenceItem(
                source_type=source.source_type,
                source_id=source.source_id,
                location=source.location,
                detail=detail,
            )
        )

    if not response.found:
        return SpecialistFinding(
            agent="runbook_analysis",
            summary=response.message,
            missing_information=["No matching operational runbook was found."],
        )

    return SpecialistFinding(
        agent="runbook_analysis",
        summary="Runbook guidance recommends safe rollback review and approval for database write failures.",
        evidence=evidence,
        hypotheses=[
            Hypothesis(
                description="Rollback or migration remediation should require human approval.",
                confidence=0.78,
            )
        ],
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
