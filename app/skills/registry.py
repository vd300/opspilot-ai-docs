from app.skills.contracts import SkillName, SkillRunner
from app.skills.deployment_comparison import DeploymentComparisonSkill
from app.skills.incident_timeline import IncidentTimelineSkill
from app.skills.log_investigation import LogInvestigationSkill
from app.skills.runbook_retrieval import RunbookRetrievalSkill

_SKILLS: dict[SkillName, SkillRunner] = {
    "log_investigation": LogInvestigationSkill(),
    "deployment_comparison": DeploymentComparisonSkill(),
    "incident_timeline": IncidentTimelineSkill(),
    "runbook_retrieval": RunbookRetrievalSkill(),
}


def get_skill(name: SkillName) -> SkillRunner:
    return _SKILLS[name]


def list_skills() -> list[SkillName]:
    return list(_SKILLS)
