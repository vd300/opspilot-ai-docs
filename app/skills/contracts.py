from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, Field

SkillName = Literal[
    "log_investigation",
    "deployment_comparison",
    "incident_timeline",
    "runbook_retrieval",
]


class SkillExecutionContext(BaseModel):
    request_id: str | None = None
    investigation_id: str | None = None
    agent_name: str | None = None


class SkillRequest(BaseModel):
    context: SkillExecutionContext = SkillExecutionContext()


class SkillResult(BaseModel):
    skill_name: SkillName
    found: bool
    message: str
    missing_information: list[str] = Field(default_factory=list)


RequestT = TypeVar("RequestT", bound=SkillRequest)
ResultT = TypeVar("ResultT", bound=SkillResult)


class SkillRunner(Protocol[RequestT, ResultT]):
    name: SkillName

    def execute(self, request: RequestT) -> ResultT:
        ...
