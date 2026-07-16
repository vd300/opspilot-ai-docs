import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.router.classifiers import RouteClassifier, UnavailableClassifier
from app.router.schemas import OpsRoute, RouteDecision, RouterInput
from app.shopflow.repositories import ShopFlowRepository

logger = logging.getLogger("opspilot.router")

MIN_CLASSIFIER_CONFIDENCE = 0.75

INCIDENT_ID_PATTERN = re.compile(r"\bINC-\d+\b", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"\bv\d+(?:\.\d+){1,3}\b", re.IGNORECASE)
DEPLOYMENT_ID_PATTERN = re.compile(r"\bdeploy-[a-z0-9-]+\b", re.IGNORECASE)
SERVICE_LIKE_PATTERN = re.compile(r"\b[a-z][a-z0-9-]+-(?:service|database)\b", re.IGNORECASE)


class RequestRouter:
    def __init__(
        self,
        *,
        classifier: RouteClassifier | None = None,
        repository: ShopFlowRepository | None = None,
        min_classifier_confidence: float = MIN_CLASSIFIER_CONFIDENCE,
    ) -> None:
        self.classifier = classifier or UnavailableClassifier()
        self.repository = repository or ShopFlowRepository()
        self.min_classifier_confidence = min_classifier_confidence

    def route(self, router_input: RouterInput, *, request_id: str | None = None) -> RouteDecision:
        started_at = time.perf_counter()
        failure_type: str | None = None
        deterministic = self._deterministic_decision(router_input)

        try:
            raw_decision = self.classifier.classify(router_input)
            llm_decision = self._validate_classifier_output(raw_decision)
            llm_decision = self._merge_entities(router_input, llm_decision)
            if (
                llm_decision.confidence >= self.min_classifier_confidence
                and not self._has_obvious_supported_pattern(router_input)
            ):
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self._log_decision(llm_decision, request_id, duration_ms, None)
                return llm_decision
            failure_type = (
                "low_confidence"
                if llm_decision.confidence < self.min_classifier_confidence
                else "obvious_pattern"
            )
        except TimeoutError:
            failure_type = "timeout"
        except ValidationError:
            failure_type = "schema_validation"
        except ValueError as exc:
            failure_type = str(exc) or "unsupported_route"
        except Exception as exc:
            failure_type = "provider_error"
            logger.warning(
                "route_classifier_failed",
                extra={
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc),
                },
            )

        fallback = deterministic.model_copy(
            update={"fallback_used": True, "classification_failure_type": failure_type}
        )
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self._log_decision(fallback, request_id, duration_ms, failure_type)
        return fallback

    def _validate_classifier_output(
        self,
        raw_decision: RouteDecision | Mapping[str, Any],
    ) -> RouteDecision:
        if isinstance(raw_decision, RouteDecision):
            return raw_decision
        if isinstance(raw_decision, Mapping):
            return RouteDecision.model_validate(raw_decision)
        raise ValueError("schema_validation")

    def _deterministic_decision(self, router_input: RouterInput) -> RouteDecision:
        question = router_input.question.strip()
        entities = self._extract_entities(router_input)
        route = self._deterministic_route(question)
        reason = self._reason_for(route, question, entities["service_found"])
        confidence = 0.9 if question else 1.0
        if route == OpsRoute.GENERAL_QUESTION and question:
            confidence = 0.78

        return RouteDecision(
            route=route,
            service_name=entities["service_name"],
            service_found=entities["service_found"],
            matched_services=entities["matched_services"],
            incident_id=entities["incident_id"],
            deployment_id=entities["deployment_id"],
            confidence=confidence,
            reason=reason,
        )

    def _merge_entities(self, router_input: RouterInput, decision: RouteDecision) -> RouteDecision:
        entities = self._extract_entities(router_input)
        updates: dict[str, Any] = {
            "service_name": entities["service_name"],
            "service_found": entities["service_found"],
            "matched_services": entities["matched_services"],
            "incident_id": entities["incident_id"],
            "deployment_id": entities["deployment_id"],
        }
        return decision.model_copy(update=updates)

    def _extract_entities(self, router_input: RouterInput) -> dict[str, Any]:
        question = router_input.question
        known_services = {
            service.service_name.lower(): service.service_name
            for service in self.repository.load_services()
        }
        matched_services: list[str] = []
        unknown_service: str | None = None

        explicit_service = router_input.service_name
        if explicit_service:
            normalized = known_services.get(explicit_service.lower())
            service_name = normalized or explicit_service
            service_found = normalized is not None
            matched_services = [service_name]
        else:
            for match in SERVICE_LIKE_PATTERN.findall(question):
                normalized = known_services.get(match.lower())
                if normalized and normalized not in matched_services:
                    matched_services.append(normalized)
                elif not normalized and unknown_service is None:
                    unknown_service = match
            service_name = matched_services[0] if matched_services else unknown_service
            service_found = True if matched_services else (False if unknown_service else None)

        incident_match = INCIDENT_ID_PATTERN.search(router_input.incident_id or question)
        deployment_match = DEPLOYMENT_ID_PATTERN.search(question) or VERSION_PATTERN.search(question)

        return {
            "service_name": service_name,
            "service_found": service_found,
            "matched_services": matched_services,
            "incident_id": incident_match.group(0).upper() if incident_match else router_input.incident_id,
            "deployment_id": deployment_match.group(0) if deployment_match else None,
        }

    def _deterministic_route(self, question: str) -> OpsRoute:
        text = question.lower()
        if not text:
            return OpsRoute.GENERAL_QUESTION
        if self._contains_any(
            text,
            ("postmortem", "report", "timeline", "summarize the investigation", "incident summary"),
        ):
            return OpsRoute.REPORT_GENERATION
        if self._contains_any(
            text,
            (
                "runbook",
                "rollback steps",
                "rollback instruction",
                "rollback instructions",
                "troubleshooting",
                "procedure",
                "instructions",
                "how should we handle",
            ),
        ):
            return OpsRoute.RUNBOOK_SEARCH
        if self._contains_any(
            text,
            (
                "why",
                "failing",
                "failure",
                "failed",
                "degraded",
                "unavailable",
                "slow",
                "errors",
                "http 500",
                "500 rate",
                "caused",
                "cause",
                "investigate",
                "incident",
            ),
        ):
            return OpsRoute.INCIDENT_INVESTIGATION
        if self._contains_any(
            text,
            (
                "deployment",
                "deployments",
                "deployed",
                "release",
                "version",
                "changed",
                "changes",
                "migration",
                "v2.",
            ),
        ):
            return OpsRoute.DEPLOYMENT_ANALYSIS
        if self._contains_any(
            text,
            (
                "who owns",
                "owner",
                "ownership",
                "team supports",
                "supports",
                "contact",
                "repository",
                "repo",
                "depend on",
                "depends on",
                "dependencies",
            ),
        ):
            return OpsRoute.SERVICE_LOOKUP
        return OpsRoute.GENERAL_QUESTION

    def _has_obvious_supported_pattern(self, router_input: RouterInput) -> bool:
        return self._deterministic_route(router_input.question.strip()) != OpsRoute.GENERAL_QUESTION

    def _reason_for(self, route: OpsRoute, question: str, service_found: bool | None) -> str:
        if not question.strip():
            return "The user question is empty."
        suffix = ""
        if service_found is False:
            suffix = " The requested service was not found in the ShopFlow service catalog."
        reasons = {
            OpsRoute.REPORT_GENERATION: "The user is asking for a report, postmortem, summary, or timeline.",
            OpsRoute.INCIDENT_INVESTIGATION: "The user is asking why a service or incident is failing or behaving unexpectedly.",
            OpsRoute.DEPLOYMENT_ANALYSIS: "The user is asking about deployments, releases, versions, or changes.",
            OpsRoute.RUNBOOK_SEARCH: "The user is asking for a runbook, procedure, troubleshooting, or rollback instructions.",
            OpsRoute.SERVICE_LOOKUP: "The user is asking for ownership, contact, repository, or dependency information.",
            OpsRoute.GENERAL_QUESTION: "The request does not match a supported operational workflow.",
        }
        return reasons[route] + suffix

    def _log_decision(
        self,
        decision: RouteDecision,
        request_id: str | None,
        duration_ms: float,
        failure_type: str | None,
    ) -> None:
        logger.info(
            "route_selected",
            extra={
                "request_id": request_id,
                "route": decision.route.value,
                "confidence": decision.confidence,
                "fallback_used": decision.fallback_used,
                "classifier_duration_ms": duration_ms,
                "classification_failure_type": failure_type,
            },
        )

    @staticmethod
    def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)
