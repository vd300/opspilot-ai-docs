from datetime import datetime

from app.shopflow.repositories import ShopFlowRepository


def test_loads_all_shopflow_fixture_data() -> None:
    repository = ShopFlowRepository()

    assert len(repository.load_owners()) == 5
    assert len(repository.load_services()) == 5
    assert repository.load_dependencies()
    assert repository.load_logs()
    assert repository.load_metrics()
    assert repository.load_deployments()
    assert repository.load_runbooks()
    assert repository.load_incidents()


def test_service_identifiers_are_unique_and_expected() -> None:
    services = ShopFlowRepository().load_services()
    service_names = [service.service_name for service in services]

    assert len(service_names) == len(set(service_names))
    assert set(service_names) == {
        "checkout-service",
        "payment-service",
        "inventory-service",
        "notification-service",
        "order-database",
    }


def test_fixture_references_are_valid() -> None:
    assert ShopFlowRepository().validate_references() == []


def test_dependency_and_owner_references_are_valid() -> None:
    repository = ShopFlowRepository()
    owner_ids = {owner.owner_id for owner in repository.load_owners()}
    service_names = {service.service_name for service in repository.load_services()}

    assert all(service.owner_id in owner_ids for service in repository.load_services())
    assert all(
        dependency.source_service in service_names and dependency.target_service in service_names
        for dependency in repository.load_dependencies()
    )


def test_fixture_timestamps_are_timezone_aware() -> None:
    repository = ShopFlowRepository()
    timestamps: list[datetime] = [
        *(log.timestamp for log in repository.load_logs()),
        *(metric.timestamp for metric in repository.load_metrics()),
        *(deployment.deployed_at for deployment in repository.load_deployments()),
        *(incident.starts_at for incident in repository.load_incidents()),
    ]

    assert timestamps
    assert all(timestamp.tzinfo is not None for timestamp in timestamps)
    assert all(timestamp.utcoffset() is not None for timestamp in timestamps)


def test_inc_001_deployment_precedes_error_spike() -> None:
    repository = ShopFlowRepository()
    deployment = next(
        item for item in repository.load_deployments() if item.deployment_id == "deploy-checkout-20260714-1400"
    )
    spike = next(
        metric for metric in repository.load_metrics() if metric.metric_id == "metric-inc001-1404-500-rate"
    )

    assert deployment.deployed_at < spike.timestamp


def test_inc_001_contains_database_insert_errors() -> None:
    logs = ShopFlowRepository().load_logs()

    insert_errors = [
        log
        for log in logs
        if log.error_code == "DB_INSERT_FAILED"
        and log.fields.get("operation") == "insert"
        and log.fields.get("missing_field") == "shipping_region"
    ]

    assert insert_errors


def test_inc_001_deployment_contains_shipping_region_migration_change() -> None:
    deployments = ShopFlowRepository().load_deployments()

    migration_changes = [
        change
        for deployment in deployments
        for change in deployment.changes
        if change.change_type == "database_migration"
        and "shipping_region" in change.description
    ]

    assert migration_changes


def test_inc_001_metrics_show_http_500_increase() -> None:
    metrics = [
        metric
        for metric in ShopFlowRepository().load_metrics()
        if metric.service_name == "checkout-service"
        and metric.metric_name == "http_500_rate_percent"
    ]
    before = next(metric for metric in metrics if metric.metric_id == "metric-inc001-1359-500-rate")
    after = next(metric for metric in metrics if metric.metric_id == "metric-inc001-1404-500-rate")

    assert before.value <= 1.5
    assert after.value >= 23
    assert after.value > before.value * 10


def test_inc_001_runbook_contains_safe_rollback_guidance() -> None:
    runbook = next(
        item
        for item in ShopFlowRepository().load_runbooks()
        if item.runbook_id == "rb-checkout-db-write-failures"
    )

    guidance = " ".join(step.action.lower() for step in runbook.steps)

    assert "rollback" in guidance
    assert "approval" in guidance
    assert "default" in guidance or "backfill" in guidance


def test_inc_001_evidence_references_are_stable_and_complete() -> None:
    incident = next(
        item for item in ShopFlowRepository().load_incidents() if item.incident_id == "INC-001"
    )
    evidence_ids = [evidence.evidence_id for evidence in incident.evidence]
    evidence_types = {evidence.evidence_type for evidence in incident.evidence}

    assert len(evidence_ids) == len(set(evidence_ids))
    assert {
        "deployment",
        "log",
        "metric",
        "runbook",
        "dependency",
    }.issubset(evidence_types)

