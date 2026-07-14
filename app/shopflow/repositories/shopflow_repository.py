from pathlib import Path

from pydantic import TypeAdapter

from app.shopflow.loaders import load_json_file, load_json_files
from app.shopflow.models import (
    DeploymentRecord,
    IncidentScenario,
    LogEvent,
    MetricSnapshot,
    Runbook,
    ServiceCatalogEntry,
    ServiceDependency,
    ServiceOwner,
)


class ShopFlowRepository:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(__file__).resolve().parents[1] / "data"

    def load_owners(self) -> list[ServiceOwner]:
        return TypeAdapter(list[ServiceOwner]).validate_python(
            load_json_file(self.data_dir / "owners.json")
        )

    def load_services(self) -> list[ServiceCatalogEntry]:
        return TypeAdapter(list[ServiceCatalogEntry]).validate_python(
            load_json_file(self.data_dir / "services.json")
        )

    def load_dependencies(self) -> list[ServiceDependency]:
        return TypeAdapter(list[ServiceDependency]).validate_python(
            load_json_file(self.data_dir / "dependencies.json")
        )

    def load_logs(self) -> list[LogEvent]:
        return TypeAdapter(list[LogEvent]).validate_python(
            load_json_files(self.data_dir / "logs")
        )

    def load_metrics(self) -> list[MetricSnapshot]:
        return TypeAdapter(list[MetricSnapshot]).validate_python(
            load_json_files(self.data_dir / "metrics")
        )

    def load_deployments(self) -> list[DeploymentRecord]:
        return TypeAdapter(list[DeploymentRecord]).validate_python(
            load_json_files(self.data_dir / "deployments")
        )

    def load_runbooks(self) -> list[Runbook]:
        return TypeAdapter(list[Runbook]).validate_python(
            load_json_files(self.data_dir / "runbooks")
        )

    def load_incidents(self) -> list[IncidentScenario]:
        return TypeAdapter(list[IncidentScenario]).validate_python(
            load_json_files(self.data_dir / "incidents")
        )

    def validate_references(self) -> list[str]:
        errors: list[str] = []
        owners = {owner.owner_id for owner in self.load_owners()}
        services = {service.service_name for service in self.load_services()}
        dependencies = self.load_dependencies()
        logs = {log.event_id for log in self.load_logs()}
        metrics = {metric.metric_id for metric in self.load_metrics()}
        deployments = {deployment.deployment_id for deployment in self.load_deployments()}
        runbooks = {runbook.runbook_id for runbook in self.load_runbooks()}

        for service in self.load_services():
            if service.owner_id not in owners:
                errors.append(f"{service.service_name} references unknown owner {service.owner_id}")

        for dependency in dependencies:
            if dependency.source_service not in services:
                errors.append(f"{dependency.dependency_id} has unknown source service")
            if dependency.target_service not in services:
                errors.append(f"{dependency.dependency_id} has unknown target service")

        for event in self.load_logs():
            if event.service_name not in services:
                errors.append(f"{event.event_id} references unknown service")

        for metric in self.load_metrics():
            if metric.service_name not in services:
                errors.append(f"{metric.metric_id} references unknown service")

        for deployment in self.load_deployments():
            if deployment.service_name not in services:
                errors.append(f"{deployment.deployment_id} references unknown service")

        for runbook in self.load_runbooks():
            for service_name in runbook.service_names:
                if service_name not in services:
                    errors.append(f"{runbook.runbook_id} references unknown service {service_name}")

        source_ids_by_type = {
            "deployment": deployments,
            "log": logs,
            "metric": metrics,
            "runbook": runbooks,
            "service": services,
            "dependency": {dependency.dependency_id for dependency in dependencies},
        }
        for incident in self.load_incidents():
            if incident.service_name not in services:
                errors.append(f"{incident.incident_id} references unknown service")
            for service_name in incident.related_services:
                if service_name not in services:
                    errors.append(f"{incident.incident_id} references unknown related service {service_name}")
            for runbook_id in incident.related_runbook_ids:
                if runbook_id not in runbooks:
                    errors.append(f"{incident.incident_id} references unknown runbook {runbook_id}")
            for evidence in incident.evidence:
                valid_source_ids = source_ids_by_type[evidence.evidence_type]
                if evidence.source_id not in valid_source_ids:
                    errors.append(
                        f"{incident.incident_id} evidence {evidence.evidence_id} "
                        f"references unknown {evidence.evidence_type} {evidence.source_id}"
                    )

        return errors
