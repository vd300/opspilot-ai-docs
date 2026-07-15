from pydantic import BaseModel, Field


class SkillEvidence(BaseModel):
    source_type: str
    source_id: str
    location: str
    detail: str
    timestamp: str | None = None


class TimelineEvent(BaseModel):
    source_id: str
    source_type: str
    timestamp: str
    detail: str
    location: str


class TimelineResult(BaseModel):
    events: list[TimelineEvent] = Field(default_factory=list)
    summary: str
