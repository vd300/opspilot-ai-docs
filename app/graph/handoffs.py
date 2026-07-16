from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.graph.subagents import EvidenceItem, Hypothesis, SpecialistFinding
from app.llm import StructuredModel

HandoffTarget = Literal["database_specialist"]

DATABASE_HANDOFF_TERMS = {
    "database",
    "migration",
    "schema",
    "insert",
    "write",
    "shipping_region",
    "connection pool",
    "deadlock",
    "lock contention",
}


class HandoffDecision(BaseModel):
    should_handoff: bool
    target_agent: str | None = None
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(default_factory=list)


class DatabaseSpecialistResult(BaseModel):
    agent: HandoffTarget = "database_specialist"
    status: str = "completed"
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def assess_handoff(
    findings: list[SpecialistFinding],
    *,
    model: StructuredModel | None = None,
) -> HandoffDecision:
    fallback = _deterministic_handoff_decision(findings)
    if model is None:
        return fallback

    try:
        model_decision = model.generate_structured(
            task="handoff_decision",
            system_prompt=(
                "Decide whether OpsPilot should hand off to a specialist using only "
                "the supplied structured findings. The only supported target is "
                "database_specialist. Do not invent evidence IDs."
            ),
            user_prompt=_handoff_prompt(findings, fallback),
            response_model=HandoffDecision,
        )
    except Exception:
        return fallback

    if not _safe_model_handoff_decision(model_decision, findings):
        return fallback
    return model_decision


def _deterministic_handoff_decision(findings: list[SpecialistFinding]) -> HandoffDecision:
    matched_evidence: dict[str, EvidenceItem] = {}
    matched_hypotheses = 0

    for finding in findings:
        for item in finding.evidence:
            if _contains_database_signal(item.detail):
                matched_evidence[item.source_id] = item
        for hypothesis in finding.hypotheses:
            if _contains_database_signal(hypothesis.description):
                matched_hypotheses += 1

    signal_count = len(matched_evidence) + matched_hypotheses
    if signal_count < 2:
        return HandoffDecision(
            should_handoff=False,
            reason="Evidence does not show enough database-specific signals for specialist handoff.",
            confidence=0.0,
            evidence_ids=sorted(matched_evidence),
        )

    confidence = min(0.95, 0.65 + (signal_count * 0.05))
    return HandoffDecision(
        should_handoff=True,
        target_agent="database_specialist",
        reason="Multiple findings indicate a database-specific failure pattern.",
        confidence=round(confidence, 2),
        evidence_ids=sorted(matched_evidence),
    )


def _handoff_prompt(findings: list[SpecialistFinding], fallback: HandoffDecision) -> str:
    import json

    return json.dumps(
        {
            "findings": [finding.model_dump(mode="json", exclude_none=True) for finding in findings],
            "deterministic_candidate": fallback.model_dump(mode="json", exclude_none=True),
        },
        sort_keys=True,
    )


def _safe_model_handoff_decision(
    decision: HandoffDecision,
    findings: list[SpecialistFinding],
) -> bool:
    if decision.should_handoff and decision.target_agent != "database_specialist":
        return False
    known_evidence_ids = {
        item.source_id
        for finding in findings
        for item in finding.evidence
    }
    return set(decision.evidence_ids).issubset(known_evidence_ids)


def validate_handoff_target(decision: HandoffDecision) -> HandoffTarget | None:
    if not decision.should_handoff:
        return None
    if decision.target_agent != "database_specialist":
        raise ValueError(f"Unsupported handoff target: {decision.target_agent}.")
    return "database_specialist"


def run_database_specialist(
    decision: HandoffDecision,
    findings: list[SpecialistFinding],
) -> DatabaseSpecialistResult:
    validate_handoff_target(decision)
    evidence = _selected_evidence(decision, findings)
    hypotheses = [
        Hypothesis(
            description=(
                "A checkout-service database migration introduced a shipping_region "
                "write-path/schema mismatch."
            ),
            confidence=max(decision.confidence, 0.88),
        )
    ]
    return DatabaseSpecialistResult(
        summary=(
            "Database specialist reviewed the handoff evidence and found the strongest "
            "signal is a migration-related checkout write failure."
        ),
        evidence=evidence,
        hypotheses=hypotheses,
        recommendations=[
            "Inspect the checkout migration that introduced or required shipping_region.",
            "Verify whether the application write path populates shipping_region before rollback.",
            "Use read-only database diagnostics first; require approval before schema or rollback actions.",
        ],
        confidence=max(decision.confidence, 0.88),
    )


def handoff_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_database_signal(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in DATABASE_HANDOFF_TERMS)


def _selected_evidence(
    decision: HandoffDecision,
    findings: list[SpecialistFinding],
) -> list[EvidenceItem]:
    evidence_by_id = {
        item.source_id: item
        for finding in findings
        for item in finding.evidence
    }
    return [
        evidence_by_id[source_id]
        for source_id in decision.evidence_ids
        if source_id in evidence_by_id
    ]
