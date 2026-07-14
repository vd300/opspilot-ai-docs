from datetime import datetime

import pytest
from pydantic import ValidationError

from app.shopflow.tools import (
    get_deployment_diff,
    get_metrics,
    get_recent_deployments,
    get_service_dependencies,
    get_service_owner,
    search_logs,
    search_runbooks,
)


def test_search_logs_returns_matching_events_with_sources() -> None:
    response = search_logs(
        service_name="checkout-service",
        query="shipping_region",
        level="ERROR",
        start_time=datetime.fromisoformat("2026-07-14T14:03:00+05:30"),
        end_time=datetime.fromisoformat("2026-07-14T14:04:00+05:30"),
    )

    assert response.found is True
    assert {log.event_id for log in response.logs} == {
        "log-inc001-140301",
        "log-inc001-140325",
    }
    assert {source.source_id for source in response.source_references} == {
        "log-inc001-140301",
        "log-inc001-140325",
    }


def test_get_metrics_returns_filtered_metric_snapshots() -> None:
    response = get_metrics(
        service_name="checkout-service",
        metric_name="http_500_rate_percent",
    )

    assert response.found is True
    assert [metric.metric_id for metric in response.metrics] == [
        "metric-inc001-1359-500-rate",
        "metric-inc001-1404-500-rate",
    ]
    assert all(source.source_type == "metric" for source in response.source_references)


def test_get_recent_deployments_returns_latest_first() -> None:
    response = get_recent_deployments(service_name="checkout-service")

    assert response.found is True
    assert response.deployments[0].deployment_id == "deploy-checkout-20260714-1400"
    assert response.source_references[0].source_id == "deploy-checkout-20260714-1400"


def test_get_deployment_diff_returns_changes_and_source() -> None:
    response = get_deployment_diff(deployment_id="deploy-checkout-20260714-1400")

    assert response.found is True
    assert response.deployment is not None
    assert any(change.change_type == "database_migration" for change in response.changes)
    assert response.source_references[0].source_type == "deployment"


def test_search_runbooks_matches_service_and_query() -> None:
    response = search_runbooks(service_name="checkout-service", query="rollback")

    assert response.found is True
    assert response.runbooks[0].runbook_id == "rb-checkout-db-write-failures"
    assert response.source_references[0].source_id == "rb-checkout-db-write-failures"


def test_get_service_owner_returns_team_contact() -> None:
    response = get_service_owner(service_name="checkout-service")

    assert response.found is True
    assert response.owner is not None
    assert response.owner.team_name == "Checkout Platform"
    assert response.source_references[0].source_id == "checkout-service"


def test_get_service_dependencies_returns_checkout_outbound_dependencies() -> None:
    response = get_service_dependencies(service_name="checkout-service")

    assert response.found is True
    assert {dependency.target_service for dependency in response.dependencies} == {
        "payment-service",
        "inventory-service",
        "order-database",
        "notification-service",
    }
    assert all(source.source_type == "dependency" for source in response.source_references)


def test_tools_handle_missing_data_without_crashing() -> None:
    owner_response = get_service_owner(service_name="missing-service")
    diff_response = get_deployment_diff(deployment_id="missing-deployment")
    log_response = search_logs(service_name="payment-service", query="shipping_region")

    assert owner_response.found is False
    assert diff_response.found is False
    assert log_response.found is False
    assert owner_response.source_references == []
    assert diff_response.source_references == []
    assert log_response.source_references == []


def test_tools_validate_inputs() -> None:
    with pytest.raises(ValidationError):
        search_logs(service_name="", limit=1)

    with pytest.raises(ValidationError):
        get_metrics(
            service_name="checkout-service",
            start_time=datetime.fromisoformat("2026-07-14T14:05:00+05:30"),
            end_time=datetime.fromisoformat("2026-07-14T14:00:00+05:30"),
        )

    with pytest.raises(ValidationError):
        search_runbooks()

    with pytest.raises(ValidationError):
        get_service_dependencies(service_name="checkout-service", direction="sideways")
