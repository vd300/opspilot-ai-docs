from pydantic import Field

from app.shopflow.tools import search_runbooks
from app.shopflow.tools.schemas import RunbookSearchResponse
from app.skills.contracts import SkillRequest, SkillResult
from app.skills.models import SkillEvidence


class RunbookRetrievalRequest(SkillRequest):
    service_name: str | None = Field(default=None, min_length=1)
    query: str = Field(default="database", min_length=1)


class RunbookRetrievalResult(SkillResult):
    skill_name: str = "runbook_retrieval"
    runbooks: list[dict] = Field(default_factory=list)
    evidence: list[SkillEvidence] = Field(default_factory=list)


class RunbookRetrievalSkill:
    name = "runbook_retrieval"

    def execute(self, request: RunbookRetrievalRequest) -> RunbookRetrievalResult:
        response = search_runbooks(
            service_name=request.service_name,
            query=request.query,
        )
        return _build_result(response)


def _build_result(response: RunbookSearchResponse) -> RunbookRetrievalResult:
    evidence = []
    for runbook, source in zip(response.runbooks, response.source_references, strict=False):
        approval_steps = [step.title for step in runbook.steps if step.requires_approval]
        detail = f"{runbook.title}: {runbook.summary}"
        if approval_steps:
            detail = f"{detail} Approval required for: {', '.join(approval_steps)}."
        evidence.append(
            SkillEvidence(
                source_type=source.source_type,
                source_id=source.source_id,
                location=source.location,
                detail=detail,
            )
        )

    return RunbookRetrievalResult(
        found=response.found,
        message=response.message,
        runbooks=[runbook.model_dump(mode="json") for runbook in response.runbooks],
        evidence=evidence,
        missing_information=[] if response.found else ["No matching operational runbook was found."],
    )
