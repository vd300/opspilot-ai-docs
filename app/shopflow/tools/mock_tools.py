from datetime import datetime

from app.shopflow.models import Environment, LogEvent, Runbook
from app.shopflow.repositories import ShopFlowRepository
from app.shopflow.tools.schemas import (
    DeploymentDiffResponse,
    DeploymentSearchResponse,
    DependencyLookupResponse,
    GetDeploymentDiffInput,
    GetMetricsInput,
    GetRecentDeploymentsInput,
    GetServiceDependenciesInput,
    GetServiceOwnerInput,
    LogSearchResponse,
    MetricSearchResponse,
    OwnerLookupResponse,
    RunbookSearchResponse,
    SearchLogsInput,
    SearchRunbooksInput,
    SourceReference,
)


def search_logs(
    *,
    service_name: str,
    environment: Environment = "production",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    query: str | None = None,
    level: str | None = None,
    limit: int = 50,
    repository: ShopFlowRepository | None = None,
) -> LogSearchResponse:
    request = SearchLogsInput(
        service_name=service_name,
        environment=environment,
        start_time=start_time,
        end_time=end_time,
        query=query,
        level=level,
        limit=limit,
    )
    repo = repository or ShopFlowRepository()
    logs = [
        log
        for log in repo.load_logs()
        if log.service_name == request.service_name
        and log.environment == request.environment
        and _within_time_window(log.timestamp, request.start_time, request.end_time)
        and (request.level is None or log.level == request.level)
        and _log_matches_query(log, request.query)
    ][: request.limit]

    return LogSearchResponse(
        found=bool(logs),
        message=_result_message("log event", len(logs), request.service_name),
        logs=logs,
        source_references=[
            SourceReference(source_type="log", source_id=log.event_id, location="shopflow.logs")
            for log in logs
        ],
    )


def get_metrics(
    *,
    service_name: str,
    environment: Environment = "production",
    metric_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    repository: ShopFlowRepository | None = None,
) -> MetricSearchResponse:
    request = GetMetricsInput(
        service_name=service_name,
        environment=environment,
        metric_name=metric_name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    repo = repository or ShopFlowRepository()
    metrics = [
        metric
        for metric in repo.load_metrics()
        if metric.service_name == request.service_name
        and metric.environment == request.environment
        and (request.metric_name is None or metric.metric_name == request.metric_name)
        and _within_time_window(metric.timestamp, request.start_time, request.end_time)
    ][: request.limit]

    return MetricSearchResponse(
        found=bool(metrics),
        message=_result_message("metric snapshot", len(metrics), request.service_name),
        metrics=metrics,
        source_references=[
            SourceReference(
                source_type="metric", source_id=metric.metric_id, location="shopflow.metrics"
            )
            for metric in metrics
        ],
    )


def get_recent_deployments(
    *,
    service_name: str,
    environment: Environment = "production",
    since: datetime | None = None,
    limit: int = 10,
    repository: ShopFlowRepository | None = None,
) -> DeploymentSearchResponse:
    request = GetRecentDeploymentsInput(
        service_name=service_name,
        environment=environment,
        since=since,
        limit=limit,
    )
    repo = repository or ShopFlowRepository()
    deployments = sorted(
        [
            deployment
            for deployment in repo.load_deployments()
            if deployment.service_name == request.service_name
            and deployment.environment == request.environment
            and (request.since is None or deployment.deployed_at >= request.since)
        ],
        key=lambda deployment: deployment.deployed_at,
        reverse=True,
    )[: request.limit]

    return DeploymentSearchResponse(
        found=bool(deployments),
        message=_result_message("deployment", len(deployments), request.service_name),
        deployments=deployments,
        source_references=[
            SourceReference(
                source_type="deployment",
                source_id=deployment.deployment_id,
                location="shopflow.deployments",
            )
            for deployment in deployments
        ],
    )


def get_deployment_diff(
    *,
    deployment_id: str,
    repository: ShopFlowRepository | None = None,
) -> DeploymentDiffResponse:
    request = GetDeploymentDiffInput(deployment_id=deployment_id)
    repo = repository or ShopFlowRepository()
    deployment = next(
        (
            item
            for item in repo.load_deployments()
            if item.deployment_id == request.deployment_id
        ),
        None,
    )
    if deployment is None:
        return DeploymentDiffResponse(
            found=False,
            message=f"No deployment found for {request.deployment_id}.",
        )

    return DeploymentDiffResponse(
        found=True,
        message=f"Found deployment diff for {request.deployment_id}.",
        deployment=deployment,
        changes=deployment.changes,
        source_references=[
            SourceReference(
                source_type="deployment",
                source_id=deployment.deployment_id,
                location="shopflow.deployments",
            )
        ],
    )


def search_runbooks(
    *,
    query: str | None = None,
    service_name: str | None = None,
    limit: int = 10,
    repository: ShopFlowRepository | None = None,
) -> RunbookSearchResponse:
    request = SearchRunbooksInput(query=query, service_name=service_name, limit=limit)
    repo = repository or ShopFlowRepository()
    runbooks = [
        runbook
        for runbook in repo.load_runbooks()
        if _runbook_matches(runbook, request.query, request.service_name)
    ][: request.limit]

    target = request.service_name or request.query or "runbook search"
    return RunbookSearchResponse(
        found=bool(runbooks),
        message=_result_message("runbook", len(runbooks), target),
        runbooks=runbooks,
        source_references=[
            SourceReference(
                source_type="runbook",
                source_id=runbook.runbook_id,
                location="shopflow.runbooks",
            )
            for runbook in runbooks
        ],
    )


def get_service_owner(
    *,
    service_name: str,
    environment: Environment = "production",
    repository: ShopFlowRepository | None = None,
) -> OwnerLookupResponse:
    request = GetServiceOwnerInput(service_name=service_name, environment=environment)
    repo = repository or ShopFlowRepository()
    service = next(
        (
            item
            for item in repo.load_services()
            if item.service_name == request.service_name and item.environment == request.environment
        ),
        None,
    )
    if service is None:
        return OwnerLookupResponse(
            found=False,
            message=f"No service found for {request.service_name} in {request.environment}.",
        )

    owner = next((item for item in repo.load_owners() if item.owner_id == service.owner_id), None)
    if owner is None:
        return OwnerLookupResponse(
            found=False,
            message=f"No owner found for {request.service_name}.",
            service=service,
            source_references=[
                SourceReference(
                    source_type="service",
                    source_id=service.service_name,
                    location="shopflow.services",
                )
            ],
        )

    return OwnerLookupResponse(
        found=True,
        message=f"Found owner for {request.service_name}.",
        service=service,
        owner=owner,
        source_references=[
            SourceReference(
                source_type="service",
                source_id=service.service_name,
                location="shopflow.services",
            )
        ],
    )


def get_service_dependencies(
    *,
    service_name: str,
    environment: Environment = "production",
    direction: str = "outbound",
    repository: ShopFlowRepository | None = None,
) -> DependencyLookupResponse:
    request = GetServiceDependenciesInput(
        service_name=service_name,
        environment=environment,
        direction=direction,
    )
    repo = repository or ShopFlowRepository()
    service = next(
        (
            item
            for item in repo.load_services()
            if item.service_name == request.service_name and item.environment == request.environment
        ),
        None,
    )
    if service is None:
        return DependencyLookupResponse(
            found=False,
            message=f"No service found for {request.service_name} in {request.environment}.",
        )

    dependencies = [
        dependency
        for dependency in repo.load_dependencies()
        if _dependency_matches_direction(
            dependency.source_service,
            dependency.target_service,
            request.service_name,
            request.direction,
        )
    ]
    return DependencyLookupResponse(
        found=bool(dependencies),
        message=_result_message("dependency", len(dependencies), request.service_name),
        service=service,
        dependencies=dependencies,
        source_references=[
            SourceReference(
                source_type="dependency",
                source_id=dependency.dependency_id,
                location="shopflow.dependencies",
            )
            for dependency in dependencies
        ],
    )


def _within_time_window(
    timestamp: datetime,
    start_time: datetime | None,
    end_time: datetime | None,
) -> bool:
    if start_time and timestamp < start_time:
        return False
    if end_time and timestamp > end_time:
        return False
    return True


def _log_matches_query(log: LogEvent, query: str | None) -> bool:
    if query is None:
        return True
    needle = query.lower()
    haystack = " ".join(
        [
            log.message,
            log.component,
            log.error_code or "",
            *[str(value) for value in log.fields.values() if value is not None],
        ]
    ).lower()
    return needle in haystack


def _runbook_matches(
    runbook: Runbook,
    query: str | None,
    service_name: str | None,
) -> bool:
    if service_name and service_name not in runbook.service_names:
        return False
    if query is None:
        return True
    needle = query.lower()
    haystack = " ".join(
        [
            runbook.title,
            runbook.summary,
            *runbook.symptoms,
            *[step.title for step in runbook.steps],
            *[step.action for step in runbook.steps],
        ]
    ).lower()
    return needle in haystack


def _dependency_matches_direction(
    source_service: str,
    target_service: str,
    service_name: str,
    direction: str,
) -> bool:
    outbound_match = direction in {"outbound", "both"} and source_service == service_name
    inbound_match = direction in {"inbound", "both"} and target_service == service_name
    return outbound_match or inbound_match


def _result_message(item_name: str, count: int, target: str) -> str:
    if count == 0:
        return f"No {item_name}s found for {target}."
    if count == 1:
        return f"Found 1 {item_name} for {target}."
    return f"Found {count} {item_name}s for {target}."
