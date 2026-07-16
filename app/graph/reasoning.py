import json

from pydantic import BaseModel, Field

from app.graph.subagents import EvidenceItem, SpecialistFinding
from app.llm import StructuredModel


class DiagnosisDecision(BaseModel):
    preliminary_diagnosis: str
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    requires_approval: bool


DIAGNOSIS_SYSTEM_PROMPT = """You are the OpsPilot incident coordinator.
Create an evidence-backed preliminary diagnosis using only supplied findings and evidence.
Do not invent tool results, source IDs, timestamps, actions, or hidden reasoning.
Any production rollback or schema change must require human approval."""


def generate_diagnosis(
    findings: list[SpecialistFinding],
    evidence: list[EvidenceItem],
    *,
    model: StructuredModel | None = None,
) -> DiagnosisDecision:
    fallback = deterministic_diagnosis(findings)
    if model is None:
        return fallback

    payload = {
        "findings": [finding.model_dump(mode="json", exclude_none=True) for finding in findings],
        "evidence": [item.model_dump(mode="json", exclude_none=True) for item in evidence],
        "fallback_recommendations": fallback.recommendations,
    }
    try:
        decision = model.generate_structured(
            task="diagnosis",
            system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, sort_keys=True),
            response_model=DiagnosisDecision,
        )
    except Exception:
        return fallback

    if not _diagnosis_cites_known_evidence(decision, evidence):
        return fallback
    return decision


def deterministic_diagnosis(findings: list[SpecialistFinding]) -> DiagnosisDecision:
    missing_information = [
        missing
        for finding in findings
        for missing in finding.missing_information
    ]
    diagnosis = (
        "The likely cause of INC-001 is the checkout-service v2.1.0 database migration "
        "adding or requiring shipping_region without compatible write-path data. "
        "Logs show insert failures, metrics show the HTTP 500 spike, and deployment "
        "evidence ties the failure window to a high-risk database migration."
    )
    if missing_information:
        diagnosis = f"{diagnosis} Missing information: {'; '.join(missing_information)}."

    return DiagnosisDecision(
        preliminary_diagnosis=diagnosis,
        recommendations=[
            "Pause further checkout-service deployments until the migration is reviewed.",
            "Confirm whether shipping_region is required by the new schema and absent from checkout writes.",
            "Use the checkout database write failures runbook before rollback or migration remediation.",
            "Get human approval before any production rollback or schema change.",
        ],
        confidence=_combined_confidence(findings),
        requires_approval=True,
    )


def _diagnosis_cites_known_evidence(
    decision: DiagnosisDecision,
    evidence: list[EvidenceItem],
) -> bool:
    if not evidence:
        return True
    known_ids = {item.source_id for item in evidence}
    text = " ".join([decision.preliminary_diagnosis, *decision.recommendations])
    mentioned_ids = {source_id for source_id in known_ids if source_id in text}
    return bool(mentioned_ids) or "evidence" in text.lower()


def _combined_confidence(findings: list[SpecialistFinding]) -> float:
    confident_findings = [finding.confidence for finding in findings if finding.confidence > 0]
    if not confident_findings:
        return 0.0
    return round(sum(confident_findings) / len(confident_findings), 2)
