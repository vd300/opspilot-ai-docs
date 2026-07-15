import pytest

from app.graph.subagents import SpecialistInput, run_deployment_analysis, run_log_analysis
from app.skills import get_skill, list_skills
from app.skills.deployment_comparison import (
    DeploymentComparisonRequest,
    DeploymentComparisonResult,
)
from app.skills.incident_timeline import IncidentTimelineRequest, IncidentTimelineResult
from app.skills.log_investigation import LogInvestigationRequest, LogInvestigationResult
from app.skills.models import SkillEvidence
from app.skills.runbook_retrieval import RunbookRetrievalRequest, RunbookRetrievalResult


def test_skill_registry_exposes_phase_7_skills() -> None:
    assert set(list_skills()) == {
        "deployment_comparison",
        "incident_timeline",
        "log_investigation",
        "runbook_retrieval",
    }


def test_log_investigation_skill_reuses_shopflow_log_tool() -> None:
    skill = get_skill("log_investigation")
    result = LogInvestigationResult.model_validate(
        skill.execute(
            LogInvestigationRequest(
                service_name="checkout-service",
                environment="production",
            )
        )
    )

    assert result.found is True
    assert result.first_failure_timestamp is not None
    assert any(item.source_id == "log-inc001-140301" for item in result.evidence)


def test_log_investigation_skill_reports_missing_data() -> None:
    skill = get_skill("log_investigation")
    result = LogInvestigationResult.model_validate(
        skill.execute(
            LogInvestigationRequest(
                service_name="missing-service",
                environment="production",
            )
        )
    )

    assert result.found is False
    assert result.missing_information


def test_deployment_comparison_skill_identifies_database_migration() -> None:
    skill = get_skill("deployment_comparison")
    result = DeploymentComparisonResult.model_validate(
        skill.execute(
            DeploymentComparisonRequest(
                service_name="checkout-service",
                environment="production",
            )
        )
    )

    assert result.found is True
    assert result.has_database_migration is True
    assert any(item.source_id == "deploy-checkout-20260714-1400" for item in result.evidence)


def test_runbook_retrieval_skill_returns_approval_evidence() -> None:
    skill = get_skill("runbook_retrieval")
    result = RunbookRetrievalResult.model_validate(
        skill.execute(
            RunbookRetrievalRequest(
                service_name="checkout-service",
                query="database",
            )
        )
    )

    assert result.found is True
    assert any(item.source_id == "rb-checkout-db-write-failures" for item in result.evidence)
    assert any("approval" in item.detail.lower() for item in result.evidence)


def test_incident_timeline_skill_orders_timestamped_evidence() -> None:
    skill = get_skill("incident_timeline")
    result = IncidentTimelineResult.model_validate(
        skill.execute(
            IncidentTimelineRequest(
                evidence=[
                    SkillEvidence(
                        source_type="log",
                        source_id="later",
                        location="shopflow.logs",
                        timestamp="2026-07-14T14:04:00+05:30",
                        detail="later event",
                    ),
                    SkillEvidence(
                        source_type="deployment",
                        source_id="earlier",
                        location="shopflow.deployments",
                        timestamp="2026-07-14T14:00:00+05:30",
                        detail="earlier event",
                    ),
                ]
            )
        )
    )

    assert [event.source_id for event in result.events] == ["earlier", "later"]


def test_incident_timeline_skill_reports_missing_timestamped_evidence() -> None:
    skill = get_skill("incident_timeline")
    result = IncidentTimelineResult.model_validate(
        skill.execute(
            IncidentTimelineRequest(
                evidence=[
                    SkillEvidence(
                        source_type="runbook",
                        source_id="rb-1",
                        location="shopflow.runbooks",
                        detail="no timestamp",
                    )
                ]
            )
        )
    )

    assert result.found is False
    assert result.missing_information


def test_incident_timeline_skill_is_reused_by_multiple_agents() -> None:
    input_data = SpecialistInput(
        service_name="checkout-service",
        environment="production",
        incident_id="INC-001",
    )

    log_finding = run_log_analysis(input_data)
    deployment_finding = run_deployment_analysis(input_data)

    assert "incident_timeline" in log_finding.skills_used
    assert "incident_timeline" in deployment_finding.skills_used
