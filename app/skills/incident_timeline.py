from datetime import datetime

from pydantic import Field

from app.skills.contracts import SkillRequest, SkillResult
from app.skills.models import SkillEvidence, TimelineEvent


class IncidentTimelineRequest(SkillRequest):
    evidence: list[SkillEvidence] = Field(default_factory=list)


class IncidentTimelineResult(SkillResult):
    skill_name: str = "incident_timeline"
    events: list[TimelineEvent] = Field(default_factory=list)


class IncidentTimelineSkill:
    name = "incident_timeline"

    def execute(self, request: IncidentTimelineRequest) -> IncidentTimelineResult:
        events = [
            TimelineEvent(
                source_id=item.source_id,
                source_type=item.source_type,
                timestamp=item.timestamp,
                detail=item.detail,
                location=item.location,
            )
            for item in request.evidence
            if item.timestamp is not None
        ]
        events = sorted(events, key=lambda event: datetime.fromisoformat(event.timestamp))
        if not events:
            return IncidentTimelineResult(
                found=False,
                message="No timestamped evidence was available for timeline generation.",
                missing_information=["Timestamped evidence is required to build an incident timeline."],
            )
        return IncidentTimelineResult(
            found=True,
            message=f"Created incident timeline with {len(events)} event(s).",
            events=events,
        )
