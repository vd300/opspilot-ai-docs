import json

from app.llm import StructuredModel
from app.router.schemas import OpsRoute, RouteDecision, RouterInput

ROUTER_SYSTEM_PROMPT = """You classify OpsPilot AI user requests.
Return only structured data matching the schema.
Use one of the supported routes and do not invent service, incident, or deployment data.
Do not include hidden reasoning."""


class LLMRouteClassifier:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    def classify(self, router_input: RouterInput) -> RouteDecision:
        payload = {
            "question": router_input.question,
            "conversation_context": router_input.conversation_context,
            "service_name": router_input.service_name,
            "incident_id": router_input.incident_id,
            "supported_routes": [route.value for route in OpsRoute],
        }
        return self.model.generate_structured(
            task="route_classification",
            system_prompt=ROUTER_SYSTEM_PROMPT,
            user_prompt=json.dumps(payload, sort_keys=True),
            response_model=RouteDecision,
        )
