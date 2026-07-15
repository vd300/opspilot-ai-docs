from pydantic import Field

from app.shopflow.tools import get_deployment_diff, get_recent_deployments
from app.skills.contracts import SkillRequest, SkillResult
from app.skills.models import SkillEvidence


class DeploymentComparisonRequest(SkillRequest):
    service_name: str = Field(min_length=1)
    environment: str = "production"
    deployment_id: str | None = None


class DeploymentComparisonResult(SkillResult):
    skill_name: str = "deployment_comparison"
    deployment: dict | None = None
    changes: list[dict] = Field(default_factory=list)
    evidence: list[SkillEvidence] = Field(default_factory=list)
    has_database_migration: bool = False


class DeploymentComparisonSkill:
    name = "deployment_comparison"

    def execute(self, request: DeploymentComparisonRequest) -> DeploymentComparisonResult:
        deployments_response = get_recent_deployments(
            service_name=request.service_name,
            environment=request.environment,  # type: ignore[arg-type]
            limit=1,
        )
        if not deployments_response.found or not deployments_response.deployments:
            return DeploymentComparisonResult(
                found=False,
                message=deployments_response.message,
                missing_information=["No recent deployment was found for the service."],
            )

        deployment = deployments_response.deployments[0]
        diff_response = get_deployment_diff(
            deployment_id=request.deployment_id or deployment.deployment_id
        )
        evidence = [
            SkillEvidence(
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
                SkillEvidence(
                    source_type="deployment",
                    source_id=change.change_id,
                    location=change.path,
                    timestamp=deployment.deployed_at.isoformat(),
                    detail=f"{change.change_type}: {change.description}",
                )
            )

        has_database_migration = any(
            change.change_type == "database_migration" for change in diff_response.changes
        )
        return DeploymentComparisonResult(
            found=True,
            message=diff_response.message,
            deployment=deployment.model_dump(mode="json"),
            changes=[change.model_dump(mode="json") for change in diff_response.changes],
            evidence=evidence,
            has_database_migration=has_database_migration,
        )
