from typing import Protocol, runtime_checkable

from app.router.schemas import RouteDecision, RouterInput


@runtime_checkable
class RouteClassifier(Protocol):
    def classify(self, router_input: RouterInput) -> RouteDecision | dict:
        """Return structured route classification output."""


class UnavailableClassifier:
    def classify(self, router_input: RouterInput) -> RouteDecision | dict:
        raise RuntimeError("No LLM classifier is configured.")
