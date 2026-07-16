import os

import pytest

from app.core.config import Settings
from app.graph.dependencies import GraphDependencies
from app.graph.handoffs import HandoffDecision, assess_handoff
from app.graph.nodes import make_aggregate_evidence_node
from app.graph.reasoning import DiagnosisDecision
from app.graph.subagents import EvidenceItem, Hypothesis, SpecialistFinding
from app.llm import FakeStructuredModel, ModelConfiguration, OpenAIResponsesStructuredModel, create_structured_model
from app.llm.models import _strict_json_schema
from app.router import OpsRoute, RouteDecision, RouterInput
from app.router.llm_classifier import LLMRouteClassifier
from app.router.service import RequestRouter


def test_model_factory_uses_stub_provider_by_default() -> None:
    model = create_structured_model(Settings(_env_file=None))

    assert isinstance(model, FakeStructuredModel)


def test_model_factory_requires_credentials_for_openai_provider() -> None:
    settings = Settings(model_provider="openai", model_api_key=None)

    assert create_structured_model(settings) is None


def test_openai_model_can_be_constructed_when_credentials_exist() -> None:
    model = OpenAIResponsesStructuredModel(
        ModelConfiguration(
            provider="openai",
            model_name="gpt-4.1-mini",
            api_key="test-key",
        )
    )

    assert model.config.model_name == "gpt-4.1-mini"


def test_openai_structured_schema_is_strict() -> None:
    schema = _strict_json_schema(RouteDecision)

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["$defs"]["OpsRoute"]["enum"]


def test_llm_route_classifier_uses_structured_output() -> None:
    fake_model = FakeStructuredModel(
        {
            "route_classification": {
                "route": "runbook_search",
                "confidence": 0.94,
                "reason": "The user is asking for an operational procedure.",
            }
        }
    )

    decision = RequestRouter(classifier=LLMRouteClassifier(fake_model)).route(
        RouterInput(question="Need assistance.")
    )

    assert decision.route == OpsRoute.RUNBOOK_SEARCH
    assert decision.fallback_used is False
    assert fake_model.calls[0]["task"] == "route_classification"


def test_model_assisted_diagnosis_is_validated_and_injected() -> None:
    finding = SpecialistFinding(
        agent="log_analysis",
        summary="Logs show insert failures.",
        evidence=[
            EvidenceItem(
                source_type="log",
                source_id="log-inc001-140301",
                location="shopflow.logs",
                detail="shipping_region insert failure",
            )
        ],
        hypotheses=[
            Hypothesis(
                description="Database migration caused write-path mismatch.",
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )
    fake_model = FakeStructuredModel(
        {
            "diagnosis": DiagnosisDecision(
                preliminary_diagnosis="Evidence log-inc001-140301 indicates a migration write-path mismatch.",
                recommendations=["Get human approval before rollback."],
                confidence=0.91,
                requires_approval=True,
            )
        }
    )
    node = make_aggregate_evidence_node(
        GraphDependencies(
            router=RequestRouter(),
            reasoning_model=fake_model,
        )
    )

    result = node({"specialist_findings": [finding.model_dump(mode="json")], "errors": []})

    assert result["preliminary_diagnosis"].startswith("Evidence log-inc001-140301")
    assert result["recommendations"] == ["Get human approval before rollback."]
    assert result["confidence"] == 0.91


def test_model_handoff_decision_rejects_invented_evidence_ids() -> None:
    finding = SpecialistFinding(
        agent="deployment_analysis",
        summary="Deployment had database migration.",
        evidence=[
            EvidenceItem(
                source_type="deployment",
                source_id="deploy-checkout-20260714-1400",
                location="shopflow.deployments",
                detail="database migration added shipping_region",
            )
        ],
        hypotheses=[
            Hypothesis(
                description="database migration failure",
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )
    fake_model = FakeStructuredModel(
        {
            "handoff_decision": HandoffDecision(
                should_handoff=True,
                target_agent="database_specialist",
                reason="Invented evidence should be rejected.",
                confidence=0.99,
                evidence_ids=["made-up-source"],
            )
        }
    )

    decision = assess_handoff([finding], model=fake_model)

    assert decision.reason == "Multiple findings indicate a database-specific failure pattern."
    assert decision.evidence_ids == ["deploy-checkout-20260714-1400"]


@pytest.mark.skipif(
    os.getenv("APP_LIVE_MODEL_VALIDATION_ENABLED") != "true"
    or not os.getenv("APP_MODEL_API_KEY"),
    reason="Live model validation is optional and requires credentials.",
)
def test_optional_live_model_validation_when_credentials_exist() -> None:
    settings = Settings(
        model_provider="openai",
        model_api_key=os.environ["APP_MODEL_API_KEY"],
    )
    model = create_structured_model(settings)
    assert model is not None

    decision = LLMRouteClassifier(model).classify(
        RouterInput(question="Who owns checkout-service?")
    )

    assert decision.route in set(OpsRoute)
    assert 0 <= decision.confidence <= 1
