from app.graph.subagents import (
    SpecialistInput,
    collect_unique_evidence,
    run_deployment_analysis,
    run_log_analysis,
    run_metrics_analysis,
    run_runbook_analysis,
    run_specialist_subagents,
)


def inc001_input(service_name: str = "checkout-service") -> SpecialistInput:
    return SpecialistInput(
        service_name=service_name,
        environment="production",
        incident_id="INC-001",
        user_query="Why is checkout-service returning HTTP 500 after the latest deployment?",
    )


def test_log_analysis_agent_returns_structured_insert_failure() -> None:
    finding = run_log_analysis(inc001_input())

    assert finding.agent == "log_analysis"
    assert finding.evidence
    assert any(item.source_id == "log-inc001-140301" for item in finding.evidence)
    assert any("shipping_region" in hypothesis.description for hypothesis in finding.hypotheses)


def test_metrics_analysis_agent_identifies_http_500_spike() -> None:
    finding = run_metrics_analysis(inc001_input())

    assert finding.agent == "metrics_analysis"
    assert {item.source_id for item in finding.evidence} == {
        "metric-inc001-1359-500-rate",
        "metric-inc001-1404-500-rate",
    }
    assert finding.confidence > 0.8


def test_deployment_analysis_agent_identifies_database_migration() -> None:
    finding = run_deployment_analysis(inc001_input())

    assert finding.agent == "deployment_analysis"
    assert any(item.source_id == "deploy-checkout-20260714-1400" for item in finding.evidence)
    assert any("database migration" in hypothesis.description for hypothesis in finding.hypotheses)


def test_runbook_agent_returns_approval_guidance() -> None:
    finding = run_runbook_analysis(inc001_input())

    assert finding.agent == "runbook_analysis"
    assert any(item.source_id == "rb-checkout-db-write-failures" for item in finding.evidence)
    assert any("approval" in item.detail.lower() for item in finding.evidence)


def test_parallel_specialists_support_partial_failures() -> None:
    findings = run_specialist_subagents(inc001_input(service_name="missing-service"))

    assert {finding.agent for finding in findings} == {
        "deployment_analysis",
        "log_analysis",
        "metrics_analysis",
        "runbook_analysis",
    }
    assert any(finding.missing_information for finding in findings)
    assert all(isinstance(finding.errors, list) for finding in findings)


def test_evidence_aggregation_deduplicates_sources_safely() -> None:
    findings = run_specialist_subagents(inc001_input())
    evidence = collect_unique_evidence(findings)

    source_ids = {item.source_id for item in evidence}
    assert "log-inc001-140301" in source_ids
    assert "metric-inc001-1404-500-rate" in source_ids
    assert "deploy-checkout-20260714-1400" in source_ids
    assert "rb-checkout-db-write-failures" in source_ids
